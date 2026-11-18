const defaultSleep = (ms, signal) =>
  new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(abortError());
      return;
    }
    const timer = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    function onAbort() {
      clearTimeout(timer);
      reject(abortError());
    }
    signal?.addEventListener("abort", onAbort, { once: true });
  });

function abortError() {
  const error = new Error("Indexing status polling was cancelled.");
  error.name = "AbortError";
  return error;
}

/**
 * Poll an indexing job until it completes or fails.
 *
 * - Stops with an error after `timeoutMs`.
 * - Tolerates up to `maxConsecutiveErrors` transient request failures
 *   (a 401/403/404 response is never retried).
 * - Stops immediately when `signal` is aborted (e.g. on logout).
 */
export async function pollIndexJob({
  jobId,
  fetchJob,
  onProgress = () => {},
  signal,
  intervalMs = 1000,
  timeoutMs = 20 * 60 * 1000,
  maxConsecutiveErrors = 5,
  now = () => Date.now(),
  sleep = defaultSleep,
}) {
  const deadline = now() + timeoutMs;
  let consecutiveErrors = 0;

  while (true) {
    if (signal?.aborted) {
      throw abortError();
    }

    let job;
    try {
      job = await fetchJob(jobId, { signal });
      consecutiveErrors = 0;
    } catch (error) {
      if (error?.name === "AbortError" || [401, 403, 404].includes(error?.status)) {
        throw error;
      }
      consecutiveErrors += 1;
      if (consecutiveErrors >= maxConsecutiveErrors) {
        throw error;
      }
    }

    if (job?.status === "completed") {
      return job;
    }

    if (job?.status === "failed") {
      throw new Error(job.error || "Repository indexing failed.");
    }

    if (job) {
      onProgress(job);
    }

    if (now() >= deadline) {
      throw new Error(
        "Indexing is taking longer than expected. Check back later or try reindexing."
      );
    }

    await sleep(intervalMs, signal);
  }
}
