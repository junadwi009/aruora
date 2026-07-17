# IELTS Coach — UI screenshots (redesign reference)

Full-page captures at 1440px wide, 2× scale, English UI (app default).
Captured from the local dev stack via a real Chrome (Playwright).

## Journey / auth flow
| File | Screen |
|---|---|
| 01-welcome | Welcome / landing |
| 02-login | Sign in |
| 03-forgot | Forgot password |
| 04-onboarding-1-name | Onboarding step 1 — name |
| 05-onboarding-2-goal | Onboarding step 2 — goal |
| 06-onboarding-3-target | Onboarding step 3 — target band |
| 07-placement-intro | Placement test intro |
| 08-placement-listening | Placement — Listening section |
| 09-placement-reading | Placement — Reading section |
| 10-placement-writing | Placement — Writing section |
| 11-placement-speaking | Placement — Speaking section |
| 12-generating | "Building your plan" loader |
| 13-results | Placement results (band + radar) |
| 14-register | Create account (save results) |
| 15-program | Choose study program (30/90/180 day) |
| 16-milestones | Program milestones timeline |

## Main app (post-onboarding shell)
| File | Screen |
|---|---|
| 17-app-home | Home dashboard |
| 18-app-reading | Reading practice |
| 19-app-listening | Listening practice |
| 20-app-speaking | Speaking practice |
| 21-app-writing | Writing practice |
| 22-app-pronounce | Pronounce |
| 23-app-vocab | Vocab (flashcards) |
| 24-app-test | Mock Test |
| 25-app-tips | Tips |
| 26-app-progress | Progress |
| 27-app-settings | Settings |

## Notes
- Bands/levels shown (A1/A2, B1…) come from a throwaway placement run, not real data.
- Not captured (sub-flows reached only from in-page actions): guided **Session**
  (Home → Start) and **Roleplay** (Home → Roleplay / Speaking).
- Captured with the API temporarily in `stub` mode for deterministic content;
  the stack was restored to `live` afterwards.
