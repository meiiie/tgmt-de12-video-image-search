import { isTauri } from "@tauri-apps/api/core";
import { open, save } from "@tauri-apps/plugin-dialog";

type PathRequest =
  | { kind: "video"; title: string }
  | { kind: "directory"; title: string }
  | { kind: "export"; title: string; defaultPath: string };

export async function choosePaths(request: PathRequest): Promise<string[]> {
  if (isTauri()) {
    const selected =
      request.kind === "export"
        ? await save({
            title: request.title,
            defaultPath: request.defaultPath,
            filters: [{ name: "MP4 video", extensions: ["mp4"] }],
          })
        : await open({
            title: request.title,
            directory: request.kind === "directory",
            multiple: request.kind === "video",
            filters:
              request.kind === "video"
                ? [
                    {
                      name: "Video",
                      extensions: [
                        "mp4",
                        "mkv",
                        "mov",
                        "avi",
                        "webm",
                        "m4v",
                        "mts",
                      ],
                    },
                  ]
                : undefined,
          });
    return selected === null
      ? []
      : typeof selected === "string"
        ? [selected]
        : selected;
  }
  return new Promise((resolve) => {
    const dialog = document.createElement("dialog");
    dialog.className = "path-dialog";
    dialog.setAttribute("aria-labelledby", "path-dialog-title");
    const form = document.createElement("form");
    const heading = document.createElement("h2");
    heading.id = "path-dialog-title";
    heading.textContent = request.title;
    const hint = document.createElement("p");
    hint.textContent =
      request.kind === "export"
        ? "Nhập đường dẫn đầy đủ cho file MP4 mới trên máy. File đã có sẽ được giữ nguyên."
        : "Dán đường dẫn trên máy của bạn. Video được đọc tại chỗ; không tải lên mạng.";
    const label = document.createElement("label");
    label.textContent =
      request.kind === "video"
        ? "Đường dẫn video (mỗi dòng một file)"
        : "Đường dẫn đầy đủ";
    const input = document.createElement("textarea");
    input.required = true;
    input.rows = request.kind === "video" ? 4 : 2;
    input.spellcheck = false;
    input.value = request.kind === "export" ? request.defaultPath : "";
    label.append(input);
    const actions = document.createElement("div");
    actions.className = "button-row";
    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.textContent = "Huỷ";
    const submit = document.createElement("button");
    submit.type = "submit";
    submit.className = "primary";
    submit.textContent =
      request.kind === "export" ? "Xuất clip" : "Dùng đường dẫn";
    const finish = (paths: string[]) => {
      dialog.close();
      dialog.remove();
      resolve(paths);
    };
    cancel.addEventListener("click", () => finish([]));
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      finish([]);
    });
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const paths = input.value
        .split(/\r?\n/)
        .map((path) => path.trim().replace(/^"(.*)"$/, "$1"))
        .filter(Boolean);
      if (!paths.length || (request.kind !== "video" && paths.length !== 1)) {
        input.setCustomValidity("Nhập một đường dẫn đầy đủ.");
        input.reportValidity();
        return;
      }
      finish(paths);
    });
    input.addEventListener("input", () => input.setCustomValidity(""));
    actions.append(cancel, submit);
    form.append(heading, hint, label, actions);
    dialog.append(form);
    document.body.append(dialog);
    dialog.showModal();
    input.focus();
  });
}
