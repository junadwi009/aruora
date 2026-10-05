import {test,expect,type Page} from "@playwright/test";

// All accounts and responses in this file are synthetic. No real backend,
// SMTP, Google login or paid inference is used by these browser regressions.
async function fixtureApi(page:Page,signedIn:boolean){
  await page.addInitScript(()=>localStorage.setItem("ielts.lang","en"));
  await page.route("**/api/**",async route=>{
    const path=new URL(route.request().url()).pathname;
    let body:unknown;let status=200;
    if(path==="/api/auth/status")body={authRequired:false,authenticated:true};
    else if(path==="/api/account/me"){
      status=signedIn?200:401;
      body=signedIn?{id:1001,name:"Synthetic Learner",email:"learner@example.com",goal:"study_abroad",targetBand:6.5,skillTargets:{},country:"",examDate:"",bio:"",emailVerified:true,isAdmin:false,hasPassword:true}:{error:{code:"UNAUTHORIZED",message:"Not signed in"}};
    }else if(path==="/api/gate/status")body={activeSeconds:0,thresholdSeconds:25200,heartbeatSec:60,locked:false,unlocked:true,isAdmin:false};
    else if(path==="/api/health")body={ok:true,asrReady:false,googleClientId:""};
    else {status=503;body={error:{code:"TEST_FIXTURE_UNAVAILABLE",message:"Not part of this synthetic UI fixture"}};}
    await route.fulfill({status,contentType:"application/json",body:JSON.stringify(body)});
  });
}

for(const viewport of [{width:1440,height:600},{width:390,height:844}]){
  test(`writing page is wheel-scrollable and its action is not clipped ${viewport.width}`,async({page})=>{
    await page.setViewportSize(viewport);await fixtureApi(page,true);
    await page.goto("/app/writing");
    await expect(page.getByRole("heading",{name:"Writing studio"})).toBeVisible();
    const region=page.locator('#aruora-content');
    await expect(region).toHaveCSS("overflow-y","auto");
    await region.hover({position:{x:10,y:40}});
    await page.mouse.wheel(0,6000);
    await expect.poll(()=>region.evaluate(el=>el.scrollTop)).toBeGreaterThan(0);
    const action=page.getByRole("button",{name:"Get practice feedback"});
    await expect(action).toBeInViewport();
    const box=await action.boundingBox();
    const navigation=page.locator(".aru-mobile-tabs");
    const navBox=await navigation.isVisible()?await navigation.boundingBox():null;
    expect(box).not.toBeNull();
    expect(box!.y+box!.height).toBeLessThanOrEqual((navBox?.y??viewport.height)+1);
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.x+box!.width).toBeLessThanOrEqual(viewport.width);
  });
}

test("login backoff takes precedence over legacy unauthorized code",async({page})=>{
  await fixtureApi(page,false);
  await page.route("**/api/account/login",route=>route.fulfill({status:429,contentType:"application/json",headers:{"Retry-After":"42"},body:JSON.stringify({error:{code:"UNAUTHORIZED",message:"Try later",details:{retryAfter:42}}})}));
  await page.goto("/login");
  await page.getByLabel("Email",{exact:true}).fill("learner@example.com");
  await page.locator('input[autocomplete="current-password"]').fill("synthetic test passphrase");
  await page.getByRole("button",{name:"Log in to my workspace"}).click();
  await expect(page.getByRole("alert")).toContainText("Too many sign-in attempts");
  await expect(page.getByRole("button",{name:/Retry in/})).toBeDisabled();
  await expect(page).toHaveURL(/\/login/);
});

test("MFA rejection reveals and focuses the code input",async({page})=>{
  await fixtureApi(page,false);
  await page.route("**/api/account/login",route=>route.fulfill({status:401,contentType:"application/json",body:JSON.stringify({error:{code:"ADMIN_MFA_REQUIRED",message:"MFA required"}})}));
  await page.goto("/login");
  await page.getByLabel("Email",{exact:true}).fill("learner@example.com");
  await page.locator('input[autocomplete="current-password"]').fill("synthetic test passphrase");
  await page.getByRole("button",{name:"Log in to my workspace"}).click();
  await expect(page.locator(".aru-mfa-details")).toHaveAttribute("open","");
  await expect(page.getByLabel(/MFA code/)).toBeFocused();
});

test("session bootstrap failure remains fail closed with retry",async({page})=>{
  await fixtureApi(page,false);
  await page.route("**/api/auth/status",route=>route.fulfill({status:503,contentType:"application/json",body:JSON.stringify({error:{code:"UNAVAILABLE",message:"Synthetic outage"}})}));
  await page.goto("/login");
  await expect(page.getByRole("heading",{name:"We can't confirm your session."})).toBeVisible();
  await expect(page.getByRole("button",{name:"Try again"})).toBeVisible();
  await expect(page.locator(".aru-workspace")).toHaveCount(0);
});
