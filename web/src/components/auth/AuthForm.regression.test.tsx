import {afterEach,beforeEach,describe,expect,it,vi} from "vitest";
import {cleanup,fireEvent,render,screen,waitFor} from "@testing-library/react";
import {api,ApiError} from "../../lib/api/client";
import {request} from "../../experience/learning/api";
import {AuthForm} from "./AuthForm";
import {authFailure} from "./authFailure";

vi.mock("../../lib/i18n",()=>({useT:()=>({lang:"en"})}));
vi.mock("../../experience/views",()=>({Icon:()=>null}));
vi.mock("./GoogleButton",()=>({GoogleButton:()=>null}));
vi.mock("../../experience/learning/api",()=>({request:vi.fn()}));
vi.mock("../../lib/api/client",async()=>{
  const actual=await vi.importActual<typeof import("../../lib/api/client")>("../../lib/api/client");
  return {...actual,api:{...actual.api,health:vi.fn(),accountRegister:vi.fn()}};
});
beforeEach(()=>{
  vi.clearAllMocks();
  vi.mocked(api.health).mockResolvedValue({ok:true,asrReady:false,googleClientId:""} as Awaited<ReturnType<typeof api.health>>);
});
afterEach(()=>cleanup());
function submit(){
  fireEvent.change(screen.getByLabelText("Email"),{target:{value:"learner@example.com"}});
  fireEvent.change(screen.getByLabelText(/^Password/,{selector:"input"}),{target:{value:"synthetic test passphrase"}});
  fireEvent.click(screen.getByRole("button",{name:"Log in to my workspace"}));
}
describe("login failure recovery",()=>{
  it("shows throttling instead of bad credentials for legacy 429",async()=>{
    const error=Object.assign(new ApiError("UNAUTHORIZED","Throttled",{retryAfter:42}),{status:429});
    vi.mocked(request).mockRejectedValue(error);
    const success=vi.fn();render(<AuthForm mode="login" onSuccess={success}/>);submit();
    await waitFor(()=>expect(screen.getByRole("alert")).toHaveTextContent("Too many sign-in attempts"));
    expect(screen.getByRole("button",{name:/Retry in/})).toBeDisabled();
    expect(success).not.toHaveBeenCalled();
  });
  it("opens and focuses MFA when the server requires it",async()=>{
    vi.mocked(request).mockRejectedValue(new ApiError("ADMIN_MFA_REQUIRED","MFA required"));
    render(<AuthForm mode="login" onSuccess={vi.fn()}/>);submit();
    const input=screen.getByLabelText(/MFA code/);
    await waitFor(()=>expect(input).toHaveFocus());
    expect(input.closest("details")).toHaveAttribute("open");
  });
  it("never accepts a malformed successful account payload",async()=>{
    vi.mocked(request).mockResolvedValue({ok:true});
    const success=vi.fn();render(<AuthForm mode="login" onSuccess={success}/>);submit();
    await waitFor(()=>expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(success).not.toHaveBeenCalled();
    expect(screen.getByRole("button",{name:"Log in to my workspace"})).toBeEnabled();
  });
  it("classifies network failure without exposing exception text",()=>{
    const result=authFailure(new Error("private stack trace"),"en");
    expect(result.message).not.toContain("private");
    expect(result.credentials).toBe(false);
  });
  it("uses Retry-After headers before legacy details",()=>{
    const error=Object.assign(new ApiError("RATE_LIMITED","",{retryAfter:60}),{status:429,retryAfter:"12"});
    expect(authFailure(error,"en").retrySeconds).toBe(12);
  });
});
