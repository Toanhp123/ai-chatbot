# Web Research and Browser Automation

## 1. Web research architecture

Web research is an agent capability behind Tool Runtime, not a special provider-only chat mode.

Define search/fetch abstractions that preserve provenance:

```ts
interface SearchProvider {
  search(query: SearchQuery, signal: AbortSignal): Promise<SearchResult[]>;
}

interface WebFetcher {
  fetch(url: string, options: FetchOptions, signal: AbortSignal): Promise<FetchedDocument>;
}
```

An optional extractor can normalize readable content, metadata and links without discarding the original source URL.

Do not hard-code one search vendor into conversation logic.

## 2. Research workflow

A research task should be able to:

1. decompose a broad question into evidence needs;
2. run focused searches;
3. fetch relevant sources;
4. retain source metadata and retrieval time;
5. distinguish primary/secondary sources where useful;
6. synthesize with citations;
7. preserve an inspectable evidence set/artifact.

Never describe stale model memory as live web research.

## 3. Source and citation model

A fetched/search item should preserve:

- canonical/final URL;
- title/publisher;
- retrieved timestamp;
- content type;
- snippet/extracted ranges;
- search provider/fetch provenance;
- optional published/updated timestamp;
- hash/cache metadata.

Citations link generated claims to source records/ranges when technically possible.

## 4. Web security

Web content is untrusted input.

- fetched text cannot override system/project permissions;
- do not send secrets because a page asks for them;
- enforce network request limits/timeouts/redirect policy;
- block dangerous local/internal addresses according to SSRF policy when fetching remote URLs;
- distinguish user-explicit localhost access from arbitrary model-selected localhost access;
- sanitize rendered HTML and never grant it Electron privileges.

## 5. Browser automation — later advanced capability

Browser automation is not part of the initial chat core. When implemented, prefer an isolated Playwright-controlled browser context/process rather than reusing the user's normal logged-in Chrome profile.

Potential tools:

- navigate;
- inspect accessible page/document state;
- click;
- type;
- screenshot;
- read console logs;
- limited network inspection;
- download/upload only with explicit policy.

## 6. Browser permissions

Sensitive browser actions require clear approval/policy, especially:

- login/authentication;
- submitting forms;
- purchases/financial actions;
- sending messages;
- uploading private files;
- downloading/executing files;
- clipboard/credential access.

Do not automatically import browser cookies or user profiles to bypass authentication boundaries.

## 7. Session isolation

Browser sessions should have:

- explicit storage directory/lifetime;
- project/task association;
- clear persistent vs disposable mode;
- network/download limits;
- cancellation and process cleanup;
- audit of material actions.

## 8. Roadmap

Search/fetch research mode belongs to advanced agent work after core coding-agent permissions are proven. Full interactive browser automation follows only after sandbox/permission/browser threat model is implemented and tested.
