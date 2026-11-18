import assert from "node:assert/strict";
import test from "node:test";

import { pollIndexJob } from "./pollIndexJob.js";

const noSleep = async () => {};

function jobSequence(...responses) {
  let index = 0;
  return async () => {
    const next = responses[Math.min(index, responses.length - 1)];
    index += 1;
    if (next instanceof Error) throw next;
    return next;
  };
}

test("resolves when the job completes and reports progress", async () => {
  const stages = [];
  const job = await pollIndexJob({
    jobId: "job-1",
    fetchJob: jobSequence(
      { status: "running", stage: "Cloning" },
      { status: "completed", chunk_count: 4 },
    ),
    onProgress: (current) => stages.push(current.stage),
    sleep: noSleep,
  });

  assert.equal(job.chunk_count, 4);
  assert.deepEqual(stages, ["Cloning"]);
});

test("rejects with the job error when indexing fails", async () => {
  await assert.rejects(
    pollIndexJob({
      jobId: "job-1",
      fetchJob: jobSequence({ status: "failed", error: "Too large" }),
      sleep: noSleep,
    }),
    /Too large/,
  );
});

test("retries transient request failures", async () => {
  const job = await pollIndexJob({
    jobId: "job-1",
    fetchJob: jobSequence(
      new Error("network down"),
      new Error("network down"),
      { status: "completed" },
    ),
    sleep: noSleep,
  });

  assert.equal(job.status, "completed");
});

test("gives up after too many consecutive failures", async () => {
  await assert.rejects(
    pollIndexJob({
      jobId: "job-1",
      fetchJob: jobSequence(new Error("network down")),
      maxConsecutiveErrors: 3,
      sleep: noSleep,
    }),
    /network down/,
  );
});

test("does not retry authorization errors", async () => {
  let calls = 0;
  const unauthorized = Object.assign(new Error("Invalid or expired token."), { status: 401 });
  await assert.rejects(
    pollIndexJob({
      jobId: "job-1",
      fetchJob: async () => {
        calls += 1;
        throw unauthorized;
      },
      sleep: noSleep,
    }),
    /expired/,
  );
  assert.equal(calls, 1);
});

test("times out when the job never finishes", async () => {
  let clock = 0;
  await assert.rejects(
    pollIndexJob({
      jobId: "job-1",
      fetchJob: jobSequence({ status: "running" }),
      timeoutMs: 5000,
      now: () => clock,
      sleep: async (ms) => {
        clock += ms;
      },
    }),
    /longer than expected/,
  );
});

test("stops when aborted", async () => {
  const controller = new AbortController();
  const polling = pollIndexJob({
    jobId: "job-1",
    fetchJob: jobSequence({ status: "running" }),
    signal: controller.signal,
    intervalMs: 60_000,
  });

  setTimeout(() => controller.abort(), 10);

  await assert.rejects(polling, { name: "AbortError" });
});
