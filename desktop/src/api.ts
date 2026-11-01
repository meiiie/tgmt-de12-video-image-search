import { invoke, isTauri } from "@tauri-apps/api/core";
import { z } from "zod";

export const Connection = z.object({
  port: z.number().int().min(1).max(65535),
  token: z.string().min(32),
});
export type Connection = z.infer<typeof Connection>;
export const Video = z.object({
  id: z.string(),
  path: z.string(),
  name: z.string(),
  status: z.enum(["queued", "indexing", "ready", "error", "cancelled"]),
  duration: z.number(),
  width: z.number(),
  height: z.number(),
  frames: z.number(),
  total: z.number(),
  error: z.string(),
  first_frame_id: z.number().nullable(),
});
export type Video = z.infer<typeof Video>;
export const Settings = z.object({
  fps: z.number(),
  batch_size: z.number(),
  vision_tokens: z.union([z.literal(70), z.literal(140), z.literal(280)]),
  model_path: z.string(),
  paused: z.boolean(),
});
export type Settings = z.infer<typeof Settings>;
export const Library = z.object({
  videos: z.array(Video),
  settings: Settings,
  folders: z.array(z.string()),
  history: z.array(z.string()),
  model: z.object({ state: z.string(), error: z.string(), device: z.string() }),
  summary: z.object({
    videos: z.number(),
    ready: z.number(),
    frames: z.number(),
    duration: z.number(),
    saved: z.number(),
  }),
  active: z.string().nullable(),
  data_dir: z.string(),
});
export type Library = z.infer<typeof Library>;
export const Moment = z.object({
  video_id: z.string(),
  name: z.string(),
  path: z.string(),
  duration: z.number(),
  frame_id: z.number().nullable(),
  start: z.number(),
  end: z.number(),
  peak: z.number(),
});
export type Moment = z.infer<typeof Moment>;
export const Result = Moment.extend({ score: z.number() });
export type Result = z.infer<typeof Result>;
export const Saved = Moment.extend({
  id: z.string(),
  label: z.string(),
  created: z.number(),
});
export type Saved = z.infer<typeof Saved>;
export const SearchResults = z.object({
  results: z.array(Result),
  elapsed_ms: z.number(),
  indexed_frames: z.number(),
});
export type SearchResults = z.infer<typeof SearchResults>;
export const Ok = z.object({ ok: z.boolean() });
export const Imported = z.object({
  added: z.number(),
  errors: z.array(z.string()),
  discovered: z.number(),
});

export async function connect(): Promise<Connection> {
  if (isTauri()) return Connection.parse(await invoke("connection"));
  const params = new URLSearchParams(location.hash.slice(1));
  return Connection.parse({
    port: Number(params.get("port")),
    token: params.get("token"),
  });
}

export class Api {
  constructor(readonly connection: Connection) {}
  async request<T>(
    path: string,
    schema: z.ZodType<T>,
    method = "GET",
    body?: unknown,
  ): Promise<T> {
    const response = await fetch(
      `http://127.0.0.1:${this.connection.port}${path}`,
      {
        method,
        headers: {
          Authorization: `Bearer ${this.connection.token}`,
          "Content-Type": "application/json",
        },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: AbortSignal.timeout(300_000),
      },
    );
    const payload: unknown = await response.json();
    if (!response.ok) {
      const error = z
        .object({
          detail: z.union([z.string(), z.array(z.object({ msg: z.string() }))]),
        })
        .safeParse(payload);
      throw new Error(
        error.success
          ? typeof error.data.detail === "string"
            ? error.data.detail
            : error.data.detail.map((e) => e.msg).join("; ")
          : `Lỗi xử lý (${response.status})`,
      );
    }
    return schema.parse(payload);
  }
  media(path: string): string {
    return `http://127.0.0.1:${this.connection.port}${path}?token=${encodeURIComponent(this.connection.token)}`;
  }
}

export function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
export function timestamp(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  return s >= 3600
    ? `${Math.floor(s / 3600)}:${String(Math.floor(s / 60) % 60).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`
    : `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}
