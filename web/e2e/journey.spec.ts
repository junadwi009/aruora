import { test, expect, type Page } from "@playwright/test";
import { randomBytes } from "node:crypto";

// Runs against the REAL running local application. No mocked routes or fake
// login. The write test refuses non-loopback hosts and deletes only its own
// randomly created test account. No email-verification or CSRF guard is disabled.
const loopback=new Set(["localhost","127.0.0.1","[::1]"]);
function requireLocal(url:string){if(!loopback.has(new URL(url).hostname))throw new Error("Data-writing E2E is restricted to an isolated localhost stack.");}
async function csrf(page:Page,apiOrigin:string){
  const cookies=await page.context().cookies(apiOrigin);
  return cookies.find(c=>c.name==="ar_csrf")?.value??"";
}
async function localAccountCleanup(page:Page,apiOrigin:string,email:string,password:string,userId:number){
  requireLocal(apiOrigin);
  const origin=new URL(page.url()).origin;
  const login=await page.request.post(apiOrigin+"/api/account/login",{
    headers:{Origin:origin,"X-CSRF-Token":await csrf(page,apiOrigin)},data:{email,password},
  });
  expect(login.status(),"Restore our own test session for cleanup").toBe(200);
  const own=await (await page.request.get(apiOrigin+"/api/account/me")).json();
  expect(own.id,"Never delete a different account").toBe(userId);
  expect(own.email).toBe(email);
  const deleted=await page.request.delete(apiOrigin+"/api/account",{
    headers:{Origin:origin,"X-CSRF-Token":await csrf(page,apiOrigin)},
  });
  expect(deleted.status(),"Own test-account cleanup").toBe(200);
}

test("public landing is independent of account state",async({page})=>{
  const errors:string[]=[];page.on("pageerror",e=>errors.push(e.message));
  await page.goto("/");
  await expect(page.getByRole("heading",{level:1})).toContainText("Your next chapter");
  await expect(page.getByRole("link",{name:"Start your journey",exact:true})).toBeVisible();
  expect(errors).toEqual([]);
});
test("Indonesian translates the public landing",async({page})=>{
  await page.goto("/");
  await page.getByLabel("Interface language").selectOption("id");
  await expect(page.getByRole("heading",{level:1})).toContainText("Babak barumu");
  await expect(page.getByRole("link",{name:"Mulai perjalananmu",exact:true})).toBeVisible();
});
test("landing login link opens the real sign-in screen",async({page})=>{
  await page.goto("/");
  await page.getByRole("link",{name:"Log in",exact:true}).first().click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("button",{name:"Log in to my workspace"})).toBeVisible();
});
test("Get started opens registration before protected setup",async({page})=>{
  await page.goto("/");
  await page.getByRole("link",{name:"Start your journey",exact:true}).click();
  await expect(page).toHaveURL(/\/register$/);
  await expect(page.getByRole("button",{name:"Create my account"})).toBeVisible();
  await expect(page.locator(".aru-workspace")).toHaveCount(0);
});
test("account -> setup -> actual learning routes -> logout -> login",async({page,baseURL})=>{
  test.setTimeout(180_000);
  requireLocal(baseURL??"http://localhost:5173");
  const email=`aruora-e2e-${randomBytes(8).toString("hex")}@example.invalid`;
  const password=`Local test ${randomBytes(18).toString("hex")}`;
  const errors:string[]=[];page.on("pageerror",e=>errors.push(e.message));
  let ownId:number|null=null,apiOrigin="";
  try{
    await page.goto("/register");
    await page.getByLabel("Email",{exact:true}).fill(email);
    await page.locator('input[autocomplete="new-password"]').fill(password);
    const registered=page.waitForResponse(r=>new URL(r.url()).pathname==="/api/account/register"&&r.request().method()==="POST");
    await page.getByRole("button",{name:"Create my account"}).click();
    const response=await registered;
    expect(response.status()).toBe(200);
    apiOrigin=new URL(response.url()).origin;requireLocal(apiOrigin);
    ownId=(await response.json()).id;
    expect(Number.isInteger(ownId)).toBe(true);
    await expect(page).toHaveURL(/\/app$/);
    await page.goto("/onboarding");
    await page.getByLabel("What should we call you?",{exact:true}).fill("Local test learner");
    await page.getByRole("radio",{name:/Study & scholarships/}).check();
    const setup=page.waitForResponse(r=>new URL(r.url()).pathname==="/api/onboarding"&&r.request().method()==="POST");
    await page.getByRole("button",{name:"Continue to placement"}).click();
    const saved=await setup;expect(saved.status()).toBe(200);
    expect((await saved.json()).id).toBe(ownId);
    const account=await (await page.request.get(apiOrigin+"/api/account/me")).json();
    expect(account.id).toBe(ownId);expect(account.email).toBe(email);
    for(const view of ["journey","practice","writing","speaking","reading","listening","vocab","pronounce","roleplay","test","tips","progress","settings"]){
      await page.goto(`/app/${view}`);
      await expect(page.locator(".aru-workspace")).toBeVisible();

      const content = page.locator("#aruora-content");
      await expect(content).toBeVisible();

      if(["journey","practice"].includes(view)){
        await expect(content).not.toHaveAttribute("role","main");
      }else{
        await expect(content).toHaveAttribute("role","main");
      }

      await expect(page.locator(".aru-demo-banner")).toHaveCount(0);
    }
    await page.setViewportSize({width:1440,height:900});
    await page.getByRole("button",{name:"Log out",exact:true}).click();
    await expect(page).toHaveURL(/\/$/);
    await page.goto("/login");
    await page.getByLabel("Email",{exact:true}).fill(email);
    await page.locator('input[autocomplete="current-password"]').fill(password);
    await page.getByRole("button",{name:"Log in to my workspace"}).click();
    await expect(page).toHaveURL(/\/app$/);
    await expect(page.locator(".aru-workspace")).toBeVisible();
    expect(errors).toEqual([]);
  }finally{
    if(ownId!==null&&apiOrigin)await localAccountCleanup(page,apiOrigin,email,password,ownId);
  }
});
for(const width of [360,390,768,1024,1440]){
  test(`responsive brand and spacing at ${width}px`,async({page})=>{
    await page.setViewportSize({width,height:900});await page.goto("/");
    const logo=page.locator(".aru-site-header .aru-logo");
    const metrics=await logo.evaluate(e=>{
      const a=e as HTMLElement,img=a.querySelector("img")!,s=getComputedStyle(a),b=a.getBoundingClientRect();
      return {actual:img.getBoundingClientRect().width,base:parseFloat(s.getPropertyValue("--ar-logo-base-width")),scale:parseFloat(s.getPropertyValue("--ar-logo-scale")),hitWidth:b.width,hitHeight:b.height};
    });
    expect(metrics.scale).toBe(0.6);expect(Math.abs(metrics.actual-metrics.base*0.6)).toBeLessThan(0.1);
    expect(metrics.hitWidth).toBeGreaterThanOrEqual(44);expect(metrics.hitHeight).toBeGreaterThanOrEqual(44);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBe(true);
    const gap=width<=767?48:width<=1199?64:72;
    for(const id of ["practice","why-aruora","faq"]){
      const p=await page.locator(`#${id}`).evaluate(e=>{const s=getComputedStyle(e);return parseFloat(s.paddingTop)+parseFloat(s.paddingBottom);});
      expect(p).toBe(gap);
    }
  });
}
