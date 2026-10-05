import {test,expect} from "@playwright/test";
import {randomUUID} from "node:crypto";

// Real production bundle -> nginx -> Flask -> PostgreSQL/Redis -> Celery.
// No page.route interception. The provider alone is the explicit offline stub.
for(const viewport of [{width:1440,height:700},{width:390,height:844}]){
  test(`real image login, queued writing and saved progress ${viewport.width}`,async({page,context},testInfo)=>{
    await page.setViewportSize(viewport);
    await page.addInitScript(()=>localStorage.setItem("ielts.lang","en"));
    const email=`browser-${randomUUID()}@example.invalid`,password=`synthetic-${randomUUID()}`;
    const origin="https://localhost:8443";
    const registered=await page.request.post("/api/account/register",{
      headers:{Origin:origin},data:{email,password,name:"Synthetic browser learner"}});
    expect(registered.status()).toBe(200);
    const csrf=(await context.cookies()).find(c=>c.name==="ar_csrf")?.value;
    expect(csrf).toBeTruthy();
    const logout=await page.request.post("/api/account/logout",{headers:{Origin:origin,"X-CSRF-Token":csrf!},data:{}});
    expect(logout.status()).toBe(200);
    await page.goto("/login?next=/app/writing");
    await expect(page.getByLabel("Email",{exact:true})).toBeVisible();
    await page.screenshot({path:testInfo.outputPath(`login-${viewport.width}.png`),fullPage:true});
    await page.getByLabel("Email",{exact:true}).fill(email);
    await page.locator('input[autocomplete="current-password"]').fill(password);
    await page.getByRole("button",{name:"Log in to my workspace"}).click();
    await expect(page.getByRole("heading",{name:"Writing studio"})).toBeVisible();
    const editor=page.locator("textarea.learn-editor");
    await editor.fill("Public transport helps people travel to school and work. Reliable services require careful planning, investment, and trained staff. Local authorities should consider affordability alongside the quality of the service. ".repeat(4));
    const region=page.locator("#aruora-content");
    await expect(region).toHaveCSS("overflow-y","auto");
    await region.hover({position:{x:10,y:40}});
    await page.mouse.wheel(0,8000);
    const submit=page.getByRole("button",{name:"Get practice feedback"});
    await expect(submit).toBeInViewport();
    const box=await submit.boundingBox();
    const mobile=page.locator(".aru-mobile-tabs");
    const navBox=await mobile.isVisible()?await mobile.boundingBox():null;
    expect(box!.y+box!.height).toBeLessThanOrEqual((navBox?.y??viewport.height)+1);
    const accepted=page.waitForResponse(r=>new URL(r.url()).pathname==="/api/writing/evaluate"&&r.request().method()==="POST");
    await submit.click();
    const receipt=await accepted;
    expect(receipt.status()).toBe(202);
    expect((await receipt.json()).jobId).toBeTruthy();
    await expect(page.getByRole("button",{name:"View saved progress"})).toBeVisible({timeout:90000});
    await page.screenshot({path:testInfo.outputPath(`feedback-${viewport.width}.png`),fullPage:true});
    await page.getByRole("button",{name:"View saved progress"}).click();
    await expect(page).toHaveURL(/\/app\/progress$/);
    await expect(page.getByRole("heading",{name:"Progress with evidence"})).toBeVisible();
    await expect(page.locator(".learn-table tbody tr")).toHaveCount(1);
    await expect(page.locator(".learn-table tbody tr")).toContainText("Writing");
    await expect(page.locator(".learn-table tbody tr")).toContainText("Demo · not assessed");
  });
}
