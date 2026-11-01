import { useCallback, useEffect, useRef, useState } from "react";
import { invoke, isTauri } from "@tauri-apps/api/core";
import { getCurrentWebview } from "@tauri-apps/api/webview";
import { choosePaths } from "./paths";
import { z } from "zod";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  Bookmark,
  Check,
  ChevronRight,
  CircleHelp,
  Clock3,
  Film,
  FolderOpen,
  HardDrive,
  ImagePlus,
  LoaderCircle,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Search,
  Settings2,
  ShieldCheck,
  Trash2,
  X,
} from "lucide-react";
import {
  Api,
  connect,
  Imported,
  Library,
  message,
  Moment,
  Ok,
  Result,
  Saved,
  SearchResults,
  Settings,
  timestamp,
  Video,
} from "./api";

type Page = "search" | "library" | "saved" | "activity" | "settings";
type Session =
  | { kind: "starting" }
  | { kind: "failed"; error: string }
  | { kind: "connected"; api: Api };
type Notice = { kind: "error" | "success"; text: string };
const navigation = [
  { id: "search", label: "Tìm khoảnh khắc", Icon: Search },
  { id: "library", label: "Thư viện", Icon: Film },
  { id: "saved", label: "Đã lưu", Icon: Bookmark },
  { id: "activity", label: "Hoạt động", Icon: Activity },
  { id: "settings", label: "Cài đặt", Icon: Settings2 },
] satisfies { id: Page; label: string; Icon: typeof Search }[];
const labels = {
  ready: "Sẵn sàng",
  queued: "Đang chờ",
  indexing: "Đang lập chỉ mục",
  cancelled: "Đã dừng",
  error: "Cần xử lý",
} satisfies Record<Video["status"], string>;

export function App() {
  const [session, setSession] = useState<Session>({ kind: "starting" });
  const start = useCallback(async () => {
    setSession({ kind: "starting" });
    try {
      const api = new Api(await connect());
      await api.request("/health", Ok);
      setSession({ kind: "connected", api });
    } catch (error) {
      setSession({ kind: "failed", error: message(error) });
    }
  }, []);
  useEffect(() => {
    void start();
  }, [start]);
  if (session.kind !== "connected")
    return (
      <div className="launch">
        <Brand />
        <h1>Không gian cho mọi thước phim.</h1>
        {session.kind === "starting" ? (
          <p>
            <LoaderCircle className="spin" /> Đang mở thư viện trên máy…
          </p>
        ) : (
          <>
            <p role="alert">{session.error}</p>
            <button onClick={() => void start()}>Thử kết nối lại</button>
            <small>
              Nếu tiến trình xử lý đã dừng, hãy đóng và mở lại FrameAtlas.
            </small>
          </>
        )}
      </div>
    );
  return <Workspace api={session.api} />;
}

function Brand() {
  return (
    <div className="brand">
      <span className="brand-mark">
        <Film size={22} />
      </span>
      <span>
        Frame<span className="brand-light">Atlas</span>
        <small>YOUR LOCAL VIDEO LIBRARY</small>
      </span>
    </div>
  );
}

function Workspace({ api }: { api: Api }) {
  const [page, setPage] = useState<Page>("search");
  const [library, setLibrary] = useState<Library | null>(null);
  const [saved, setSaved] = useState<Saved[]>([]);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [selected, setSelected] = useState<Moment | null>(null);
  const [importing, setImporting] = useState(false);
  const [connectionError, setConnectionError] = useState("");
  const refresh = useCallback(async () => {
    const [status, moments] = await Promise.all([
      api.request("/library", Library),
      api.request("/moments", z.array(Saved)),
    ]);
    setLibrary(status);
    setSaved(moments);
    setConnectionError("");
  }, [api]);
  useEffect(() => {
    let disposed = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        await refresh();
      } catch (error) {
        if (!disposed) setConnectionError(message(error));
      }
      if (!disposed) timer = setTimeout(() => void poll(), 2500);
    };
    void poll();
    return () => {
      disposed = true;
      clearTimeout(timer);
    };
  }, [refresh]);
  useEffect(() => {
    if (notice?.kind === "success") {
      const timer = setTimeout(() => setNotice(null), 6000);
      return () => clearTimeout(timer);
    }
  }, [notice]);
  const fail = useCallback(
    (error: unknown) => setNotice({ kind: "error", text: message(error) }),
    [],
  );
  const act = async (path: string, method = "POST", body?: unknown) => {
    try {
      await api.request(path, Ok, method, body);
      await refresh();
    } catch (error) {
      fail(error);
    }
  };
  const importPaths = useCallback(
    async (paths: string[]) => {
      if (!paths.length) return;
      setImporting(true);
      try {
        const result = await api.request("/import", Imported, "POST", {
          paths,
        });
        setNotice({
          kind: result.errors.length ? "error" : "success",
          text: result.errors.length
            ? result.errors.join("\n")
            : `Đã thêm ${result.added} video mới hoặc thay đổi · tìm thấy ${result.discovered} video.`,
        });
        await refresh();
      } catch (error) {
        fail(error);
      } finally {
        setImporting(false);
      }
    },
    [api, fail, refresh],
  );
  const choose = async (directory: boolean) => {
    try {
      const paths = await choosePaths({
        kind: directory ? "directory" : "video",
        title: directory ? "Chọn thư mục video" : "Thêm video",
      });
      await importPaths(paths);
    } catch (error) {
      fail(error);
    }
  };
  useEffect(() => {
    if (!isTauri()) return;
    const unlisten = getCurrentWebview().onDragDropEvent((event) => {
      if (event.payload.type === "drop") void importPaths(event.payload.paths);
    });
    return () => {
      void unlisten.then((fn) => fn());
    };
  }, [importPaths]);
  const inspectVideo = (video: Video) =>
    setSelected({
      video_id: video.id,
      name: video.name,
      path: video.path,
      duration: video.duration,
      frame_id: video.first_frame_id,
      start: 0,
      end: Math.min(10, video.duration),
      peak: 0,
    });
  const pending =
    library?.videos.filter(
      (v) => v.status === "queued" || v.status === "indexing",
    ).length ?? 0;
  const active = library?.videos.find((v) => v.id === library.active);
  return (
    <div className="workspace">
      <aside className="sidebar">
        <Brand />
        <div className="workspace-label">KHÔNG GIAN CÁ NHÂN</div>
        <nav aria-label="Điều hướng">
          {navigation.map(({ id, label, Icon }) => (
            <button
              key={id}
              className={page === id ? "nav-item active" : "nav-item"}
              onClick={() => setPage(id)}
            >
              <Icon size={18} />
              <span>{label}</span>
              {id === "saved" && !!saved.length && <b>{saved.length}</b>}
              {id === "activity" && pending > 0 && <b>{pending}</b>}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          {pending > 0 && (
            <div className="indexing-card">
              <div>
                <span
                  className={
                    library?.settings.paused
                      ? "status-dot paused"
                      : "status-dot"
                  }
                />
                {library?.settings.paused
                  ? "Đã tạm dừng"
                  : "Đang chuẩn bị thư viện"}
                <button
                  className="icon-button"
                  aria-label={
                    library?.settings.paused
                      ? "Tiếp tục lập chỉ mục"
                      : "Tạm dừng lập chỉ mục"
                  }
                  onClick={() =>
                    void act("/settings", "PATCH", {
                      paused: !library?.settings.paused,
                    })
                  }
                >
                  {library?.settings.paused ? (
                    <Play size={15} />
                  ) : (
                    <Pause size={15} />
                  )}
                </button>
              </div>
              <progress
                value={active?.frames ?? 0}
                max={Math.max(1, active?.total ?? 1)}
              />
              <small>
                {active
                  ? `${active.frames}/${active.total || "…"} khung · ${active.name}`
                  : `${pending} video trong hàng đợi`}
              </small>
            </div>
          )}
          <div className="privacy">
            <ShieldCheck size={16} />
            <span>
              Dữ liệu ở trên máy bạn<small>EG2 · Tìm kiếm cục bộ</small>
            </span>
          </div>
          <div className="version">
            FRAMEATLAS <span>0.1.0</span>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            Không gian cá nhân
            <ChevronRight size={14} />
            <strong>{navigation.find((n) => n.id === page)?.label}</strong>
          </div>
          <div className="import-actions">
            <button
              className="quiet"
              disabled={importing}
              onClick={() => void choose(false)}
            >
              <Plus size={16} />
              Thêm video
            </button>
            <button
              className="primary"
              disabled={importing}
              onClick={() => void choose(true)}
            >
              {importing ? (
                <LoaderCircle className="spin" size={16} />
              ) : (
                <FolderOpen size={16} />
              )}
              Thêm thư mục
            </button>
          </div>
        </header>
        {(notice || connectionError) && (
          <div
            className={`notice ${connectionError || notice?.kind === "error" ? "error" : "success"}`}
            role={
              connectionError || notice?.kind === "error" ? "alert" : "status"
            }
          >
            <span>
              {connectionError
                ? `Mất kết nối với bộ xử lý: ${connectionError}`
                : notice?.text}
            </span>
            <button
              className="icon-button"
              aria-label="Đóng thông báo"
              onClick={() => setNotice(null)}
            >
              <X size={16} />
            </button>
          </div>
        )}
        <div className="content-layout">
          <main className="content">
            {!library ? (
              <Empty
                Icon={LoaderCircle}
                title="Đang đọc thư viện…"
                text="Các video và khoảnh khắc đã lưu sẽ xuất hiện tại đây."
              />
            ) : (
              <>
                <div hidden={page !== "search"}>
                  <SearchPage
                    active={page === "search"}
                    api={api}
                    library={library}
                    selected={selected}
                    onSelect={setSelected}
                    fail={fail}
                    onLibrary={() => setPage("library")}
                  />
                </div>
                {page === "library" && (
                  <LibraryPage
                    api={api}
                    library={library}
                    onSelect={inspectVideo}
                    onAction={(id, action) =>
                      void act(`/videos/${id}/${action}`)
                    }
                    onRescan={async () => {
                      try {
                        const r = await api.request(
                          "/rescan",
                          Imported,
                          "POST",
                        );
                        setNotice({
                          kind: r.errors.length ? "error" : "success",
                          text: r.errors.length
                            ? r.errors.join("\n")
                            : `Đã kiểm tra ${r.discovered} video. Cập nhật ${r.added} video.`,
                        });
                        await refresh();
                      } catch (error) {
                        fail(error);
                      }
                    }}
                  />
                )}
                {page === "saved" && (
                  <>
                    <PageTitle
                      eyebrow="BỘ SƯU TẬP CỦA BẠN"
                      title="Những đoạn đáng giữ."
                      text={`${saved.length} khoảnh khắc · Sẵn sàng mở lại và xuất thành clip.`}
                    />
                    {saved.length ? (
                      <div className="results-grid">
                        {saved.map((moment) => (
                          <div key={moment.id} className="saved-wrapper">
                            <MomentCard
                              api={api}
                              moment={moment}
                              title={moment.label}
                              selected={
                                selected?.video_id === moment.video_id &&
                                selected.peak === moment.peak
                              }
                              onClick={() => setSelected(moment)}
                            />
                            <button
                              className="remove-saved"
                              onClick={() =>
                                void act(`/moments/${moment.id}`, "DELETE")
                              }
                              aria-label={`Bỏ lưu ${moment.label}`}
                            >
                              <Trash2 size={14} />
                              Bỏ lưu
                            </button>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <Empty
                        Icon={Bookmark}
                        title="Giữ lại khoảnh khắc bạn cần."
                        text="Mở một kết quả, chọn khoảng thời gian và lưu để quay lại bất cứ lúc nào."
                      />
                    )}
                  </>
                )}
                {page === "activity" && (
                  <>
                    <PageTitle
                      eyebrow="XỬ LÝ NỀN"
                      title="Thư viện đang lớn dần."
                      text="Mỗi lô khung hình được lưu ngay. Đóng ứng dụng và mở lại để tiếp tục từ tiến độ gần nhất."
                    />
                    <div className="section-toolbar">
                      <span>{pending} video đang chờ hoặc xử lý</span>
                      <button
                        onClick={() =>
                          void act("/settings", "PATCH", {
                            paused: !library.settings.paused,
                          })
                        }
                      >
                        {library.settings.paused ? (
                          <Play size={16} />
                        ) : (
                          <Pause size={16} />
                        )}{" "}
                        {library.settings.paused ? "Tiếp tục" : "Tạm dừng"}
                      </button>
                    </div>
                    {library.videos.length ? (
                      <div className="activity-list">
                        {library.videos.map((video) => (
                          <div className="activity-row" key={video.id}>
                            <span className={`status-icon ${video.status}`}>
                              {video.status === "ready" ? (
                                <Check size={18} />
                              ) : video.status === "indexing" ? (
                                <LoaderCircle className="spin" size={18} />
                              ) : (
                                <Film size={18} />
                              )}
                            </span>
                            <div className="activity-detail">
                              <strong>{video.name}</strong>
                              <span>
                                {labels[video.status]} · {video.frames} /{" "}
                                {video.total || "…"} khung hình
                              </span>
                              {video.status === "indexing" && (
                                <progress
                                  value={video.frames}
                                  max={Math.max(1, video.total)}
                                />
                              )}
                              {video.error && (
                                <p className="error-text">{video.error}</p>
                              )}
                            </div>
                            {video.status === "error" ||
                            video.status === "cancelled" ? (
                              <button
                                onClick={() =>
                                  void act(`/videos/${video.id}/retry`)
                                }
                              >
                                Thử lại
                              </button>
                            ) : (
                              video.status !== "ready" && (
                                <button
                                  className="quiet"
                                  onClick={() =>
                                    void act(`/videos/${video.id}/cancel`)
                                  }
                                >
                                  Dừng
                                </button>
                              )
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <Empty
                        Icon={Activity}
                        title="Chưa có tác vụ."
                        text="Thêm video hoặc thư mục để bắt đầu."
                      />
                    )}
                  </>
                )}
                {page === "settings" && (
                  <SettingsPage
                    api={api}
                    library={library}
                    refresh={refresh}
                    fail={fail}
                    notify={(text) => setNotice({ kind: "success", text })}
                  />
                )}
              </>
            )}
          </main>
          {selected && (
            <Inspector
              api={api}
              moment={selected}
              onClose={() => setSelected(null)}
              onSaved={async () => {
                await refresh();
                setNotice({
                  kind: "success",
                  text: "Đã lưu khoảnh khắc vào bộ sưu tập.",
                });
              }}
              fail={fail}
              notify={(text) => setNotice({ kind: "success", text })}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function PageTitle({
  eyebrow,
  title,
  text,
}: {
  eyebrow: string;
  title: string;
  text: string;
}) {
  return (
    <div className="page-title">
      <span className="eyebrow">{eyebrow}</span>
      <h1>{title}</h1>
      <p>{text}</p>
    </div>
  );
}
function Empty({
  Icon,
  title,
  text,
}: {
  Icon: typeof Search;
  title: string;
  text: string;
}) {
  return (
    <div className="empty">
      <div className="empty-icon">
        <Icon size={28} />
      </div>
      <h2>{title}</h2>
      <p>{text}</p>
    </div>
  );
}

function SearchPage({
  active,
  api,
  library,
  selected,
  onSelect,
  fail,
  onLibrary,
}: {
  active: boolean;
  api: Api;
  library: Library;
  selected: Moment | null;
  onSelect: (moment: Moment) => void;
  fail: (error: unknown) => void;
  onLibrary: () => void;
}) {
  const [text, setText] = useState("");
  const [image, setImage] = useState<{ data: string; name: string } | null>(
    null,
  );
  const [scope, setScope] = useState("");
  const [occurrence, setOccurrence] = useState("");
  const [result, setResult] = useState<SearchResults | null>(null);
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const file = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (active && (e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        setImage(null);
        requestAnimationFrame(() => input.current?.focus());
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [active]);
  const search = async (query = text) => {
    if ((!query.trim() && !image) || busy) return;
    setBusy(true);
    try {
      const response = await api.request("/search", SearchResults, "POST", {
        ...(image ? { image: image.data } : { text: query.trim() }),
        video_id: scope || null,
        occurrence: scope && occurrence ? Number(occurrence) : null,
      });
      setResult(response);
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  };
  const upload = async (file?: File) => {
    if (!file) return;
    if (file.size > 8_000_000) {
      fail(new Error("Chọn ảnh nhỏ hơn 8 MB."));
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string")
        setImage({ data: reader.result.split(",")[1], name: file.name });
    };
    reader.onerror = () => fail(new Error("Không đọc được ảnh."));
    reader.readAsDataURL(file);
  };
  return (
    <>
      <PageTitle
        eyebrow="TÌM ĐÚNG KHOẢNH KHẮC"
        title="Bạn đang tìm cảnh nào?"
        text="Mô tả bằng ngôn ngữ tự nhiên hoặc đưa vào một hình ảnh. FrameAtlas tìm trong video của bạn."
      />
      <form
        className="search-form"
        onSubmit={(event) => {
          event.preventDefault();
          void search();
        }}
      >
        <div className="search-input">
          <Search size={22} />
          <input
            ref={input}
            aria-label="Mô tả cảnh cần tìm"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={
              image
                ? `Ảnh: ${image.name}`
                : "Ví dụ: một người đi bộ trên phố sau cơn mưa…"
            }
            disabled={!!image}
          />
          {!image && <kbd>Ctrl K</kbd>}
          <button
            type="button"
            className="image-query"
            aria-label={image ? "Bỏ ảnh truy vấn" : "Tìm bằng hình ảnh"}
            onClick={() => (image ? setImage(null) : file.current?.click())}
          >
            {image ? <X size={20} /> : <ImagePlus size={20} />}
          </button>
          <button
            type="submit"
            className="primary search-submit"
            aria-label={busy ? "Đang tìm" : "Tìm kiếm"}
            aria-busy={busy}
            disabled={
              busy || !library.summary.frames || (!text.trim() && !image)
            }
          >
            {busy ? (
              <LoaderCircle className="spin" size={18} />
            ) : (
              <ArrowRight size={19} />
            )}
            <span>{busy ? "Đang tìm" : "Tìm kiếm"}</span>
          </button>
        </div>
        <input
          className="visually-hidden"
          ref={file}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          aria-label="Ảnh truy vấn"
          onChange={(e) => void upload(e.target.files?.[0])}
        />
        <div className="search-options">
          <label>
            Phạm vi{" "}
            <select value={scope} onChange={(e) => setScope(e.target.value)}>
              <option value="">Toàn bộ thư viện</option>
              {library.videos
                .filter((v) => v.frames > 0)
                .map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name}
                  </option>
                ))}
            </select>
          </label>
          {scope && (
            <label>
              Lần xuất hiện{" "}
              <select
                value={occurrence}
                onChange={(event) => setOccurrence(event.target.value)}
              >
                <option value="">Liên quan nhất</option>
                <option value="1">Đầu tiên</option>
                <option value="2">Thứ hai</option>
                <option value="3">Thứ ba</option>
                <option value="-1">Cuối cùng</option>
              </select>
            </label>
          )}
          <span>
            <ShieldCheck size={13} /> Nội dung không rời thiết bị
          </span>
        </div>
      </form>
      <div className="stats-strip">
        <div>
          <Film size={17} />
          <strong>{library.summary.videos}</strong>
          <span>video</span>
        </div>
        <div>
          <Clock3 size={17} />
          <strong>{timestamp(library.summary.duration)}</strong>
          <span>thời lượng</span>
        </div>
        <div>
          <HardDrive size={17} />
          <strong>{library.summary.frames.toLocaleString("vi-VN")}</strong>
          <span>khung đã lập chỉ mục</span>
        </div>
        <span className="library-ready">
          <span className="status-dot" />
          {library.summary.ready} video sẵn sàng
        </span>
      </div>
      {result ? (
        <>
          <div className="section-toolbar">
            <h2>{result.results.length} khoảnh khắc liên quan</h2>
            <span>
              {result.elapsed_ms.toLocaleString("vi-VN")} ms ·{" "}
              {result.indexed_frames.toLocaleString("vi-VN")} khung
            </span>
          </div>
          {result.results.length ? (
            <div className="results-grid">
              {result.results.map((moment) => (
                <MomentCard
                  key={`${moment.video_id}-${moment.peak}`}
                  api={api}
                  moment={moment}
                  selected={
                    selected?.video_id === moment.video_id &&
                    selected.peak === moment.peak
                  }
                  onClick={() => onSelect(moment)}
                />
              ))}
            </div>
          ) : (
            <Empty
              Icon={Search}
              title="Chưa tìm thấy khoảnh khắc."
              text="Thử mô tả khác hoặc kiểm tra video đã được lập chỉ mục trong phạm vi bạn chọn."
            />
          )}
          <p className="footnote">
            Độ tương đồng dùng để xếp hạng, không phải xác suất đúng. Hãy xem
            đoạn video để xác nhận nội dung.
          </p>
        </>
      ) : library.summary.frames ? (
        <>
          <div className="section-toolbar">
            <h2>Bắt đầu từ điều bạn nhớ.</h2>
            <button className="text-button" onClick={onLibrary}>
              Xem thư viện <ArrowRight size={15} />
            </button>
          </div>
          <div className="search-guide">
            <span className="guide-number">01 / MÔ TẢ MỘT CẢNH</span>
            <h2>
              Con người, hành động,
              <br />
              ánh sáng hay một địa điểm.
            </h2>
            <p>
              Truy vấn cụ thể giúp thu hẹp kết quả. Bạn cũng có thể tìm bằng một
              khung hình tham chiếu.
            </p>
            <div className="suggestions">
              {(library.history.length
                ? library.history.slice(0, 4)
                : [
                    "người đang đạp xe",
                    "a street at night",
                    "cảnh biển lúc hoàng hôn",
                  ]
              ).map((q) => (
                <button
                  key={q}
                  onClick={() => {
                    setText(q);
                    setImage(null);
                    input.current?.focus();
                  }}
                >
                  {q}
                  <ArrowRight size={13} />
                </button>
              ))}
            </div>
          </div>
        </>
      ) : (
        <div className="onboarding">
          <div className="onboarding-art">
            <Film size={54} />
            <span className="orbit one" />
            <span className="orbit two" />
          </div>
          <div>
            <span className="eyebrow">MỘT LẦN THÊM. NHIỀU LẦN TÌM.</span>
            <h2>
              Cho thư viện của bạn
              <br />
              một cách tìm mới.
            </h2>
            <p>
              Thêm video hoặc thư mục ở góc trên. EG2 xử lý các khung hình trên
              máy, rồi bạn có thể tìm và mở đúng đoạn cần dùng.
            </p>
            <ol>
              <li>
                <span>1</span>Chọn video trên máy
              </li>
              <li>
                <span>2</span>Đợi khung hình đầu tiên sẵn sàng
              </li>
              <li>
                <span>3</span>Tìm, lưu và xuất khoảnh khắc
              </li>
            </ol>
          </div>
        </div>
      )}
    </>
  );
}

function MomentCard({
  api,
  moment,
  title,
  selected,
  onClick,
}: {
  api: Api;
  moment: Moment;
  title?: string;
  selected: boolean;
  onClick: () => void;
}) {
  const result = Result.safeParse(moment);
  return (
    <button
      className={`moment-card ${selected ? "selected" : ""}`}
      onClick={onClick}
    >
      <div className="thumbnail">
        {moment.frame_id ? (
          <img
            loading="lazy"
            src={api.media(`/thumbnails/${moment.frame_id}`)}
            alt={`Khung hình tại ${timestamp(moment.peak)} trong ${moment.name}`}
          />
        ) : (
          <Film size={32} />
        )}
        <span className="time-pill">
          <Play size={10} fill="currentColor" />
          {timestamp(moment.peak)}
        </span>
        <span className="play-overlay">
          <Play size={21} />
        </span>
      </div>
      <div className="moment-info">
        <strong title={title ?? moment.name}>{title ?? moment.name}</strong>
        <div>
          <span>
            {timestamp(moment.start)} — {timestamp(moment.end)}
          </span>
          {result.success && (
            <span className="similarity" title="Độ tương đồng cosine">
              {result.data.score.toFixed(3)}
            </span>
          )}
        </div>
        {title && <small>{moment.name}</small>}
      </div>
    </button>
  );
}

function LibraryPage({
  api,
  library,
  onSelect,
  onAction,
  onRescan,
}: {
  api: Api;
  library: Library;
  onSelect: (video: Video) => void;
  onAction: (id: string, action: string) => void;
  onRescan: () => Promise<void>;
}) {
  const [filter, setFilter] = useState("");
  const [scanning, setScanning] = useState(false);
  const videos = library.videos.filter((v) =>
    v.name.toLocaleLowerCase().includes(filter.toLocaleLowerCase()),
  );
  return (
    <>
      <PageTitle
        eyebrow="TẤT CẢ THƯỚC PHIM"
        title="Một nơi. Mọi câu chuyện."
        text="Video giữ nguyên ở vị trí gốc. Thư viện chỉ lưu chỉ mục, ảnh xem trước và khoảnh khắc của bạn."
      />
      <div className="section-toolbar">
        <label className="filter-input">
          <Search size={16} />
          <input
            placeholder="Lọc theo tên video"
            aria-label="Lọc tên video"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
        </label>
        <button
          disabled={scanning}
          onClick={async () => {
            setScanning(true);
            try {
              await onRescan();
            } finally {
              setScanning(false);
            }
          }}
        >
          <RefreshCw size={15} className={scanning ? "spin" : ""} />
          Quét thay đổi
        </button>
      </div>
      {videos.length ? (
        <div className="video-list">
          {videos.map((video) => (
            <div className="video-row" key={video.id}>
              <button
                className="video-open"
                onClick={() => onSelect(video)}
                disabled={!video.duration}
              >
                <div className="video-thumb">
                  {video.first_frame_id ? (
                    <img
                      loading="lazy"
                      src={api.media(`/thumbnails/${video.first_frame_id}`)}
                      alt=""
                    />
                  ) : (
                    <Film size={23} />
                  )}
                </div>
                <div>
                  <strong>{video.name}</strong>
                  <small title={video.path}>{video.path}</small>
                  <span>
                    {timestamp(video.duration)} · {video.width || "—"} ×{" "}
                    {video.height || "—"} · {video.frames} khung
                  </span>
                </div>
              </button>
              <span className={`badge ${video.status}`}>
                {labels[video.status]}
              </span>
              {(video.status === "error" || video.status === "cancelled") && (
                <button
                  className="icon-button"
                  aria-label={`Thử lại ${video.name}`}
                  onClick={() => onAction(video.id, "retry")}
                >
                  <RefreshCw size={16} />
                </button>
              )}
              <button
                className="icon-button danger-hover"
                aria-label={`Bỏ ${video.name} khỏi thư viện`}
                title="Bỏ khỏi thư viện; giữ file gốc"
                onClick={() => onAction(video.id, "remove")}
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
      ) : (
        <Empty
          Icon={FolderOpen}
          title={
            filter ? "Không có tên video phù hợp." : "Thư viện đang chờ bạn."
          }
          text="Thêm thư mục hoặc kéo video từ Explorer vào cửa sổ FrameAtlas."
        />
      )}
    </>
  );
}

function Inspector({
  api,
  moment,
  onClose,
  onSaved,
  fail,
  notify,
}: {
  api: Api;
  moment: Moment;
  onClose: () => void;
  onSaved: () => Promise<void>;
  fail: (error: unknown) => void;
  notify: (text: string) => void;
}) {
  const player = useRef<HTMLVideoElement>(null);
  const [start, setStart] = useState(moment.start);
  const [end, setEnd] = useState(moment.end);
  const [label, setLabel] = useState(moment.name.replace(/\.[^.]+$/, ""));
  const [busy, setBusy] = useState<"save" | "export" | null>(null);
  const [mediaError, setMediaError] = useState(false);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    setStart(moment.start);
    setEnd(moment.end);
    setLabel(moment.name.replace(/\.[^.]+$/, ""));
    setMediaError(false);
    if (player.current?.readyState) player.current.currentTime = moment.peak;
  }, [moment]);
  useEffect(() => {
    setLoading(true);
  }, [moment.video_id]);
  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !document.querySelector("dialog[open]"))
        onClose();
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [onClose]);
  const valid =
    Number.isFinite(start) &&
    Number.isFinite(end) &&
    start >= 0 &&
    end > start &&
    end <= moment.duration + 0.05;
  const store = async () => {
    setBusy("save");
    try {
      await api.request("/moments", z.object({ id: z.string() }), "POST", {
        video_id: moment.video_id,
        start,
        end,
        peak: Math.max(start, Math.min(end, moment.peak)),
        label: label.trim() || moment.name,
      });
      await onSaved();
    } catch (error) {
      fail(error);
    } finally {
      setBusy(null);
    }
  };
  const exportVideo = async () => {
    try {
      const filename = `${moment.name.replace(/\.[^.]+$/, "")}-${Math.floor(start)}s.mp4`;
      const defaultPath = isTauri()
        ? filename
        : `${(await api.request("/library", Library)).data_dir}\\exports\\${filename}`;
      const [path] = await choosePaths({
        kind: "export",
        title: "Xuất đoạn video",
        defaultPath,
      });
      if (!path) return;
      setBusy("export");
      const output = await api.request(
        "/export",
        z.object({ path: z.string() }),
        "POST",
        { video_id: moment.video_id, start, end, path },
      );
      notify(`Đã xuất clip: ${output.path}`);
    } catch (error) {
      fail(error);
    } finally {
      setBusy(null);
    }
  };
  return (
    <aside className="inspector" aria-label="Chi tiết khoảnh khắc">
      <div className="inspector-heading">
        <span className="eyebrow">KHOẢNH KHẮC ĐÃ CHỌN</span>
        <button
          className="icon-button"
          aria-label="Đóng chi tiết"
          onClick={onClose}
        >
          <X size={18} />
        </button>
      </div>
      <h2 title={moment.name}>{moment.name}</h2>
      <div className="player-wrap">
        <video
          ref={player}
          controls
          preload="auto"
          src={api.media(`/media/${moment.video_id}`)}
          poster={
            moment.frame_id
              ? api.media(`/thumbnails/${moment.frame_id}`)
              : undefined
          }
          onLoadedMetadata={() => {
            if (player.current) player.current.currentTime = moment.peak;
            setLoading(false);
          }}
          onError={() => {
            setMediaError(true);
            setLoading(false);
          }}
        />
        {loading && (
          <span className="player-loading">
            <LoaderCircle className="spin" size={16} />
            Chuẩn bị bản xem trước…
          </span>
        )}
      </div>
      {mediaError && (
        <p className="error-text">
          Không mở được video. Kiểm tra file nguồn hoặc thử lại sau khi bộ xử lý
          hoàn tất chuyển mã.
        </p>
      )}
      <div className="inspector-meta">
        <span>
          {moment.name.split(".").pop()?.toUpperCase()} ·{" "}
          {timestamp(moment.duration)}
        </span>
        <button
          className="text-button"
          onClick={() => {
            if (player.current) {
              player.current.currentTime = moment.peak;
              void player.current.play().catch(fail);
            }
          }}
        >
          <Play size={12} />
          Đến kết quả
        </button>
      </div>
      <div className="segment-block">
        <div className="section-toolbar">
          <h3>Khoảng thời gian</h3>
          <span>{(end - start).toFixed(1)} giây</span>
        </div>
        <div className="segment-timeline">
          <span
            style={{
              left: `${(100 * start) / Math.max(1, moment.duration)}%`,
              width: `${(100 * (end - start)) / Math.max(1, moment.duration)}%`,
            }}
          />
          <i
            style={{
              left: `${(100 * moment.peak) / Math.max(1, moment.duration)}%`,
            }}
          />
        </div>
        <div className="time-fields">
          <label>
            Bắt đầu (giây)
            <input
              type="number"
              min="0"
              max={moment.duration}
              step="0.1"
              value={start}
              onChange={(event) => setStart(Number(event.target.value))}
            />
            <button
              className="text-button"
              onClick={() =>
                setStart(
                  Number((player.current?.currentTime ?? start).toFixed(1)),
                )
              }
            >
              Lấy vị trí phát
            </button>
          </label>
          <label>
            Kết thúc (giây)
            <input
              type="number"
              min="0"
              max={moment.duration}
              step="0.1"
              value={end}
              onChange={(event) => setEnd(Number(event.target.value))}
            />
            <button
              className="text-button"
              onClick={() =>
                setEnd(Number((player.current?.currentTime ?? end).toFixed(1)))
              }
            >
              Lấy vị trí phát
            </button>
          </label>
        </div>
        {!valid && (
          <p className="error-text">
            Điểm kết thúc phải sau điểm bắt đầu và nằm trong video.
          </p>
        )}
      </div>
      <label className="field-label">
        Tên khoảnh khắc
        <input
          value={label}
          maxLength={300}
          onChange={(e) => setLabel(e.target.value)}
        />
      </label>
      <button
        className="primary full"
        disabled={!!busy || !valid}
        onClick={() => void store()}
      >
        {busy === "save" ? (
          <LoaderCircle className="spin" size={16} />
        ) : (
          <Bookmark size={16} />
        )}
        Lưu khoảnh khắc
      </button>
      <button
        className="full"
        disabled={!!busy || !valid}
        onClick={() => void exportVideo()}
      >
        {busy === "export" ? (
          <LoaderCircle className="spin" size={16} />
        ) : (
          <ArrowDownToLine size={16} />
        )}{" "}
        {busy === "export" ? "Đang xuất clip…" : "Xuất đoạn MP4"}
      </button>
      <div className="source-info">
        <span className="eyebrow">FILE NGUỒN</span>
        <p title={moment.path}>{moment.path}</p>
        {isTauri() && (
          <button
            className="text-button"
            onClick={() =>
              void invoke("reveal", { videoId: moment.video_id }).catch(fail)
            }
          >
            <FolderOpen size={15} />
            Hiện trong thư mục
          </button>
        )}
      </div>
    </aside>
  );
}

function SettingsPage({
  api,
  library,
  refresh,
  fail,
  notify,
}: {
  api: Api;
  library: Library;
  refresh: () => Promise<void>;
  fail: (error: unknown) => void;
  notify: (text: string) => void;
}) {
  const [settings, setSettings] = useState<Settings>(library.settings);
  const [busy, setBusy] = useState(false);
  const rebuilding =
    settings.fps !== library.settings.fps ||
    settings.vision_tokens !== library.settings.vision_tokens ||
    settings.model_path !== library.settings.model_path;
  const persist = async () => {
    setBusy(true);
    try {
      await api.request("/settings", Ok, "PATCH", {
        fps: settings.fps,
        batch_size: settings.batch_size,
        vision_tokens: settings.vision_tokens,
        model_path: settings.model_path,
      });
      await refresh();
      notify("Đã lưu cài đặt.");
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  };
  const chooseModel = async () => {
    try {
      const [path] = await choosePaths({
        kind: "directory",
        title: "Chọn thư mục EmbeddingGemma 2",
      });
      if (typeof path === "string")
        setSettings((s) => ({ ...s, model_path: path }));
    } catch (error) {
      fail(error);
    }
  };
  const prepare = async () => {
    try {
      await api.request("/model/prepare", Ok, "POST");
      await refresh();
      notify(
        "Đang chuẩn bị EG2. Tiến độ tải chi tiết được ghi trong worker.log.",
      );
    } catch (error) {
      fail(error);
    }
  };
  return (
    <>
      <PageTitle
        eyebrow="THEO CÁCH CỦA BẠN"
        title="Nhẹ nhàng với máy. Riêng tư với bạn."
        text="Điều chỉnh cách FrameAtlas xử lý và lưu thư viện."
      />
      <section className="settings-card">
        <div className="settings-title">
          <HardDrive size={20} />
          <div>
            <h2>Bộ máy tìm kiếm EG2</h2>
            <p>
              EmbeddingGemma 2 · ảnh và văn bản trong cùng không gian tìm kiếm.
            </p>
          </div>
          <span
            className={`badge ${library.model.state === "ready" ? "ready" : "queued"}`}
          >
            {library.model.state === "ready"
              ? `Sẵn sàng · ${library.model.device.toUpperCase()}`
              : library.model.state === "loading"
                ? "Đang nạp model"
                : library.model.state === "downloading"
                  ? "Đang tải model"
                  : library.model.state === "error"
                    ? "Lỗi model"
                    : "Chưa nạp"}
          </span>
        </div>
        <label className="field-label">
          Thư mục model cục bộ (tuỳ chọn)
          <div className="input-with-button">
            <input
              value={settings.model_path}
              placeholder="Để trống để tải EG2 từ Hugging Face"
              onChange={(e) =>
                setSettings((s) => ({ ...s, model_path: e.target.value }))
              }
            />
            <button onClick={() => void chooseModel()}>
              <FolderOpen size={16} />
              Chọn
            </button>
          </div>
        </label>
        <p className="help-text">
          Lần đầu cần mạng để tải trọng số chính thức. Sau khi model đã có trên
          máy, tìm kiếm và xử lý video hoạt động ngoại tuyến. Trọng số EG2 được
          phát hành theo Apache 2.0; xem trang model để đọc đầy đủ điều khoản.
        </p>
        {library.model.error && (
          <p className="error-text">{library.model.error}</p>
        )}
        <div className="button-row">
          <button
            disabled={
              rebuilding ||
              ["loading", "downloading"].includes(library.model.state)
            }
            onClick={() => void prepare()}
          >
            <ArrowDownToLine size={15} />
            Chuẩn bị / thử lại model
          </button>
          <a
            className="text-button"
            href="https://huggingface.co/google/embeddinggemma-2"
            target="_blank"
            rel="noreferrer"
            onClick={
              isTauri()
                ? (event) => {
                    event.preventDefault();
                    void invoke("open_model_page").catch(fail);
                  }
                : undefined
            }
          >
            <CircleHelp size={15} />
            Thông tin & điều khoản
          </a>
        </div>
      </section>
      <section className="settings-card">
        <h2>Lập chỉ mục</h2>
        <label className="field-label">
          Mức chi tiết thị giác
          <select
            value={settings.vision_tokens}
            onChange={(event) =>
              setSettings((s) => ({
                ...s,
                vision_tokens: Settings.shape.vision_tokens.parse(
                  Number(event.target.value),
                ),
              }))
            }
          >
            <option value={70}>Nhanh — ưu tiên cảnh tổng thể</option>
            <option value={140}>Cân bằng — mặc định cho video</option>
            <option value={280}>
              Chi tiết — vật thể nhỏ và nhiều nội dung
            </option>
          </select>
        </label>
        <div className="settings-grid">
          <label className="field-label">
            Khung hình mỗi giây
            <select
              value={settings.fps}
              onChange={(event) =>
                setSettings((s) => ({ ...s, fps: Number(event.target.value) }))
              }
            >
              <option value={0.25}>0,25 — mỗi 4 giây</option>
              <option value={0.5}>0,5 — mỗi 2 giây</option>
              <option value={1}>1 — cân bằng</option>
              <option value={2}>2 — chi tiết hơn</option>
              <option value={4}>4 — chuyển động nhanh</option>
            </select>
          </label>
          <label className="field-label">
            Kích thước lô
            <select
              value={settings.batch_size}
              onChange={(event) =>
                setSettings((s) => ({
                  ...s,
                  batch_size: Number(event.target.value),
                }))
              }
            >
              {[1, 2, 4, 8, 16].map((n) => (
                <option key={n} value={n}>
                  {n} khung hình
                </option>
              ))}
            </select>
          </label>
        </div>
        <p className="help-text">
          Lấy mẫu dày hơn giúp tìm cảnh ngắn nhưng tăng thời gian và dung lượng.
          Lô nhỏ phù hợp máy ít bộ nhớ.
        </p>
        {rebuilding && (
          <p className="rebuild-note">
            Đổi model, mức chi tiết hoặc tần suất sẽ xây lại chỉ mục của toàn bộ
            thư viện. Hãy tạm dừng và đợi lô hiện tại kết thúc trước khi lưu.
            Video gốc và khoảnh khắc đã lưu được giữ nguyên.
          </p>
        )}
        <button
          className="primary"
          disabled={busy}
          onClick={() => void persist()}
        >
          {busy && <LoaderCircle size={15} className="spin" />}
          {rebuilding ? "Lưu & lập chỉ mục lại" : "Lưu cài đặt"}
        </button>
      </section>
      <section className="settings-card">
        <h2>Dữ liệu trên máy</h2>
        <p className="data-path">{library.data_dir}</p>
        <p className="help-text">
          Thư mục này chứa chỉ mục, bản xem trước, model và nhật ký vận hành.
          Sao lưu cả thư mục khi ứng dụng đã đóng để chuyển thư viện.
        </p>
        {library.folders.length > 0 && (
          <div className="folder-list">
            {library.folders.map((path) => (
              <div key={path}>
                <FolderOpen size={16} />
                <span>{path}</span>
                <button
                  className="text-button"
                  onClick={async () => {
                    try {
                      await api.request("/folders", Ok, "DELETE", {
                        paths: [path],
                      });
                      await refresh();
                    } catch (error) {
                      fail(error);
                    }
                  }}
                >
                  Ngừng theo dõi
                </button>
              </div>
            ))}
          </div>
        )}
        <div className="local-note">
          <ShieldCheck size={17} />
          <span>
            Video và truy vấn không được gửi lên dịch vụ tìm kiếm. Không có tài
            khoản hay analytics.
          </span>
        </div>
      </section>
    </>
  );
}
