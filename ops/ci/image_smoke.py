"""Full-image HTTPS smoke against a disposable localhost Compose project only.

No arbitrary target option: this script cannot register test users on a public
host. Do not reuse its synthetic-mail settings for externally exposed UAT.
"""
from __future__ import annotations

import http.cookiejar
import json
import os
from pathlib import Path
import re
import secrets
import ssl
import subprocess
import time
import urllib.error
import urllib.request

ORIGIN = "https://localhost:8443"
COMPOSE = ["docker", "compose", "-f", "docker-compose.prod.yml", "-f", "ops/ci/image-compose.yml"]


class Client:
    def __init__(self):
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=".ci/tls/cert.pem")),
            urllib.request.HTTPCookieProcessor(self.cookies))

    def call(self, method, path, payload=None, expected=200, headers=None):
        assert path.startswith("/") and not path.startswith("//")
        values = {"Origin": ORIGIN, "Accept": "application/json"}
        if method != "GET":
            values["Content-Type"] = "application/json"
            for cookie in self.cookies:
                if cookie.name == "ar_csrf":
                    values["X-CSRF-Token"] = cookie.value
        values.update(headers or {})
        request = urllib.request.Request(ORIGIN + path,
            data=None if payload is None else json.dumps(payload).encode(),
            headers=values, method=method)
        try:
            response = self.opener.open(request, timeout=15)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            data = response.read(5_000_000)
            status = response.status
            response_headers = response.headers
        assert status == expected, f"{method} {path}: expected {expected}, got {status}"
        if "application/json" in response_headers.get("Content-Type", ""):
            return json.loads(data), response_headers
        return data.decode(), response_headers

    def wait_ready(self):
        deadline = time.monotonic() + 100
        while time.monotonic() < deadline:
            try:
                body, _ = self.call("GET", "/api/health/ready")
                if body.get("ok") and body.get("checks", {}).get("db") and body["checks"].get("redis"):
                    return
            except (OSError, AssertionError):
                pass
            time.sleep(1)
        raise AssertionError("Stack did not become ready")

    def finish(self, job_id):
        deadline = time.monotonic() + 100
        while time.monotonic() < deadline:
            body, _ = self.call("GET", "/api/jobs/" + job_id)
            if body["status"] == "succeeded":
                return body["result"]
            assert body["status"] in ("queued", "running"), f"Job ended with {body.get('errorCode', body['status'])}"
            time.sleep(0.5)
        raise AssertionError("Evaluation did not finish")


def main():
    assert os.environ.get("GITHUB_ACTIONS") == "true", "Disposable CI only"
    assert os.environ.get("COMPOSE_PROJECT_NAME", "").startswith("aruora-image-"), "Wrong project scope"
    a, b = Client(), Client()
    a.wait_ready()
    html, headers = a.call("GET", "/")
    assert "ARUORA" in html
    for header in ("Content-Security-Policy", "X-Content-Type-Options", "Referrer-Policy"):
        assert headers.get(header), header
    assert not headers.get("Access-Control-Allow-Origin")
    for path in ("/login", "/app/writing", "/app/settings"):
        page, _ = a.call("GET", path)
        assert "<div id=\"root\"" in page
    assets = re.findall(r'(?:src|href)="(/assets/[^\"]+\.(?:js|css))"', html)
    assert assets, "No production assets found"
    for asset in assets:
        content, _ = a.call("GET", asset)
        assert content and not content.startswith("<!doctype html>"), "Asset unexpectedly fell back to HTML"
    credentials = {"email": "image-" + secrets.token_hex(8) + "@example.invalid",
                   "password": secrets.token_urlsafe(32), "name": "Synthetic image learner"}
    a.call("GET", "/api/account/me", expected=401)
    _, registration_headers = a.call("POST", "/api/account/register", credentials)
    cookie_headers = registration_headers.get_all("Set-Cookie", [])
    session_cookie = next(value for value in cookie_headers if value.startswith("ar_sid="))
    assert "Secure" in session_cookie and "HttpOnly" in session_cookie
    owner, _ = a.call("GET", "/api/account/me")
    assert isinstance(owner["id"], int) and owner["isAdmin"] is False
    essay = ("Public transport connects people with education and employment. "
             "Reliable services require investment, trained staff, and careful planning. "
             "Local authorities should measure demand before changing the price of tickets. ") * 4
    payload = {"essay": essay, "prompt": "Discuss investment in public transport.", "taskType": "task2"}
    key = "image-writing-" + secrets.token_hex(12)
    receipt, _ = a.call("POST", "/api/writing/evaluate", payload, expected=202,
                        headers={"Idempotency-Key": key})
    result = a.finish(receipt["jobId"])
    assert isinstance(result.get("savedId"), int)
    assert result["metrics"]["syntax"] is not None
    assert result["metrics"]["readability"]["fleschKincaidGrade"] != 0
    duplicate, _ = a.call("POST", "/api/writing/evaluate", payload, expected=202,
                          headers={"Idempotency-Key": key})
    assert duplicate["jobId"] == receipt["jobId"]
    a.call("POST", "/api/writing/evaluate", {**payload, "essay": essay + " Changed."}, expected=409,
           headers={"Idempotency-Key": key})
    a.call("POST", "/api/writing/evaluate", payload, expected=403,
           headers={"Idempotency-Key": key, "X-CSRF-Token": ""})
    rows, _ = a.call("GET", "/api/history/attempts?type=writing")
    assert sum(row["id"] == result["savedId"] for row in rows) == 1
    speaking, _ = a.call("POST", "/api/speaking/evaluate", {
        "transcript": "I learned to plan my work carefully. At first it was difficult, but practising every day helped me improve.",
        "question": "Describe something you learned.", "part": "part2"}, expected=202,
        headers={"Idempotency-Key": "image-speaking-" + secrets.token_hex(12)})
    spoken_result = a.finish(speaking["jobId"])
    assert isinstance(spoken_result.get("savedId"), int)
    assert spoken_result.get("estimateScope") == "speaking_text_estimate"
    b.call("POST", "/api/account/register", {
        "email": "other-" + secrets.token_hex(8) + "@example.invalid",
        "password": secrets.token_urlsafe(32), "name": "Other synthetic learner"})
    b.call("GET", "/api/jobs/" + receipt["jobId"], expected=404)
    b.call("GET", "/api/history/attempt/" + str(result["savedId"]), expected=404)
    subprocess.run(COMPOSE + ["restart", "api", "worker-llm"], check=True)
    a.wait_ready()
    restored_user, _ = a.call("GET", "/api/account/me")
    assert restored_user["id"] == owner["id"], "Session was lost across API restart"
    assert a.finish(receipt["jobId"])["savedId"] == result["savedId"]
    a.call("POST", "/api/account/logout", {})
    a.call("GET", "/api/account/me", expected=401)
    a.call("POST", "/api/account/login", {"email": credentials["email"], "password": credentials["password"]})
    logged_in, _ = a.call("GET", "/api/account/me")
    assert logged_in["id"] == owner["id"]
    report = {"httpsCertificateValidated": True, "productionAssets": len(assets),
              "secureHttpOnlySession": True, "writingAndSpeakingQueued": True,
              "writingMetricsPopulated": True, "idempotency": True, "csrfDenied": True,
              "crossAccountReadsDenied": True, "sessionAndResultSurviveRestart": True,
              "logoutAndLogin": True, "inferenceMode": "stub", "scope": "disposable localhost image stack"}
    Path("evidence").mkdir(exist_ok=True)
    Path("evidence/image-http-smoke.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
