export function normalizeRepositoryUrl(value) {
  try {
    const url = new URL(value.trim());
    const parts = url.pathname.split("/").filter(Boolean);

    if (
      url.protocol !== "https:" ||
      !["github.com", "www.github.com"].includes(url.hostname.toLowerCase()) ||
      url.username ||
      url.password ||
      url.search ||
      url.hash ||
      parts.length !== 2
    ) {
      return null;
    }

    return `${url.hostname.toLowerCase()}/${parts.join("/").replace(/\.git$/i, "").toLowerCase()}`;
  } catch {
    return null;
  }
}
