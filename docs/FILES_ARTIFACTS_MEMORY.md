# Files, Documents, Artifacts, and Memory

## 1. Attachments and document extraction

Attachments use a modular extraction pipeline. Preserve original metadata/content separately from extracted representations.

Initial formats:

- text;
- Markdown;
- source code;
- JSON;
- CSV;
- images;
- PDF with a suitable parser/render path.

Later formats:

- DOCX;
- XLSX;
- EPUB.

Do not reparse unchanged large files every conversation. Use content hashes and extraction-version metadata.

## 2. Attachment lifecycle

For each attachment track:

- original filename/path/source;
- MIME/type detection;
- size/hash;
- extraction status/version;
- page/sheet/section metadata where applicable;
- extracted text/chunk references;
- thumbnails/previews where safe;
- project/conversation ownership;
- deletion/retention state.

Treat extracted content as untrusted model context.

## 3. Artifacts

Artifacts are durable outputs separate from ordinary chat messages.

Initial artifact types:

- Markdown document;
- code file;
- text file;
- JSON;
- isolated HTML preview.

Later:

- diagrams;
- interactive web artifacts;
- generated reports and richer office-document exports.

Required artifact operations:

- version;
- open beside chat;
- edit;
- regenerate/create new version;
- export to workspace;
- associate with conversation/project/task;
- inspect provenance.

Generated HTML must run in a strongly isolated preview with no Electron/Node privileges and no implicit filesystem/network authority.

## 4. Artifact versioning

Prefer append/new-version semantics over destructive overwrite so the user can compare/revert generated outputs. Exporting to a workspace is a separate filesystem mutation mediated by Tool Runtime.

## 5. Memory vs history

Memory is explicit durable context, separate from raw chat history.

Conceptual entry:

```ts
interface MemoryEntry {
  id: string;
  content: string;
  scope: 'global' | 'project';
  source: MemorySource;
  createdAt: string;
  updatedAt: string;
  confidence?: number;
  enabled: boolean;
}
```

Users must be able to inspect, edit, disable and delete memory.

## 6. Automatic memory — later

A future system may suggest candidate memories from conversation, but it should not silently persist arbitrary conversation content.

A suggested memory should show:

- proposed content;
- scope;
- source conversation;
- reason/usefulness;
- accept/edit/reject action.

If automatic persistence is later introduced, it requires an explicit product/privacy decision and clear controls.

## 7. Context use

Attachments, artifacts and memory are candidates for Context Engine selection, not always-on prompt content. Their provenance/scope must survive retrieval so the model can distinguish user file, generated artifact and saved memory.
