import test from "node:test";
import assert from "node:assert/strict";

import { normalizeRepositoryUrl } from "./repositoryUrl.js";

test("normalizes valid public GitHub repository URLs", () => {
  assert.equal(
    normalizeRepositoryUrl(" https://WWW.GITHUB.COM/User/Repo.git/ "),
    "www.github.com/user/repo",
  );
});

test("rejects non-repository and non-HTTPS URLs", () => {
  assert.equal(normalizeRepositoryUrl("https://github.com/user"), null);
  assert.equal(normalizeRepositoryUrl("http://github.com/user/repo"), null);
  assert.equal(normalizeRepositoryUrl("https://gitlab.com/user/repo"), null);
  assert.equal(normalizeRepositoryUrl("https://github.com/user/repo?token=x"), null);
});
