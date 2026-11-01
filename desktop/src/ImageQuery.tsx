import { useRef, useState, type PointerEvent } from "react";

export type QueryImage = { name: string; url: string; data: string };
type Region = { x: number; y: number; width: number; height: number };
const whole: Region = { x: 0, y: 0, width: 1, height: 1 };
const clamp = (value: number, min = 0, max = 1) =>
  Math.max(min, Math.min(max, value));

export function ImageQuery({
  image,
  disabled,
  pending,
  onPending,
  onApply,
  fail,
}: {
  image: QueryImage;
  disabled: boolean;
  pending: boolean;
  onPending: (pending: boolean) => void;
  onApply: (data: string) => void;
  fail: (error: unknown) => void;
}) {
  const source = useRef<HTMLImageElement>(null);
  const anchor = useRef<{ x: number; y: number } | null>(null);
  const [region, setRegion] = useState<Region>(whole);
  const select = (next: Region) => {
    setRegion(next);
    onPending(true);
  };
  const point = (event: PointerEvent<HTMLDivElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    return {
      x: clamp((event.clientX - bounds.left) / bounds.width),
      y: clamp((event.clientY - bounds.top) / bounds.height),
    };
  };
  const move = (event: PointerEvent<HTMLDivElement>) => {
    if (disabled || !anchor.current) return;
    const end = point(event);
    const start = anchor.current;
    select({
      x: Math.min(start.x, end.x),
      y: Math.min(start.y, end.y),
      width: Math.abs(end.x - start.x),
      height: Math.abs(end.y - start.y),
    });
  };
  const crop = () => {
    try {
      const original = source.current;
      if (!original?.naturalWidth) throw new Error("Ảnh chưa sẵn sàng.");
      const x = Math.round(region.x * original.naturalWidth);
      const y = Math.round(region.y * original.naturalHeight);
      const width =
        Math.round((region.x + region.width) * original.naturalWidth) - x;
      const height =
        Math.round((region.y + region.height) * original.naturalHeight) - y;
      if (width < 4 || height < 4)
        throw new Error("Chọn vùng ảnh lớn hơn, tối thiểu 4 × 4 pixel.");
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext("2d");
      if (!context) throw new Error("Không thể cắt ảnh trong trình duyệt này.");
      context.drawImage(original, x, y, width, height, 0, 0, width, height);
      const data = canvas.toDataURL("image/png").split(",")[1];
      if (data.length > 12_000_000)
        throw new Error(
          "Vùng ảnh quá lớn. Chọn vùng nhỏ hơn hoặc dùng ảnh có độ phân giải thấp hơn.",
        );
      onApply(data);
      onPending(false);
    } catch (error) {
      fail(error);
    }
  };
  const field = (key: keyof Region, value: number) => {
    if (!Number.isFinite(value)) return;
    const next = {
      ...region,
      [key]: clamp(value / 100, key === "width" || key === "height" ? 0.01 : 0),
    };
    next.x = Math.min(next.x, 0.99);
    next.y = Math.min(next.y, 0.99);
    next.width = clamp(next.width, 0.01, 1 - next.x);
    next.height = clamp(next.height, 0.01, 1 - next.y);
    select(next);
  };
  return (
    <section className="query-image-panel" aria-label="Ảnh và vùng cần tìm">
      <div className="query-image-canvas">
        <div
          className="query-image-stage"
          role="group"
          aria-label="Khoanh vùng ảnh bằng chuột"
          onPointerDown={(event) => {
            if (disabled || event.button !== 0) return;
            event.preventDefault();
            event.currentTarget.setPointerCapture(event.pointerId);
            anchor.current = point(event);
            select({ ...anchor.current, width: 0, height: 0 });
          }}
          onPointerMove={move}
          onPointerUp={(event) => {
            move(event);
            anchor.current = null;
          }}
          onPointerCancel={() => {
            anchor.current = null;
          }}
        >
          <img
            ref={source}
            src={image.url}
            alt="Ảnh gốc để chọn chi tiết"
            draggable={false}
          />
          <div
            className="query-image-region"
            style={{
              left: `${region.x * 100}%`,
              top: `${region.y * 100}%`,
              width: `${region.width * 100}%`,
              height: `${region.height * 100}%`,
            }}
          />
        </div>
      </div>
      <div className="query-image-tools">
        <strong>Chọn chi tiết cần tìm</strong>
        {image.data !== image.url.split(",")[1] && (
          <img
            className="query-image-preview"
            src={`data:image/png;base64,${image.data}`}
            alt="Vùng ảnh dùng để tìm kiếm"
          />
        )}
        <p>
          Kéo trên ảnh để khoanh vùng. Giữ một ít bối cảnh nếu chi tiết quá nhỏ.
        </p>
        <fieldset disabled={disabled}>
          <div className="query-image-actions">
            <button
              type="button"
              onClick={crop}
              disabled={!pending || !region.width || !region.height}
            >
              Dùng vùng đã chọn
            </button>
            <button
              type="button"
              onClick={() => {
                setRegion(whole);
                onApply(image.url.split(",")[1]);
                onPending(false);
              }}
            >
              Dùng toàn ảnh
            </button>
          </div>
          <details>
            <summary>Chọn vùng bằng bàn phím</summary>
            <div className="query-image-fields">
              {(
                [
                  { key: "x", label: "Trái (%)" },
                  { key: "y", label: "Trên (%)" },
                  { key: "width", label: "Rộng (%)" },
                  { key: "height", label: "Cao (%)" },
                ] satisfies { key: keyof Region; label: string }[]
              ).map(({ key, label }) => (
                <label key={key}>
                  {label}
                  <input
                    type="number"
                    min={key === "x" || key === "y" ? 0 : 1}
                    max={100}
                    step={1}
                    value={Math.round(region[key] * 100)}
                    onChange={(event) =>
                      field(key, event.currentTarget.valueAsNumber)
                    }
                  />
                </label>
              ))}
            </div>
          </details>
        </fieldset>
        <p className="query-image-state" aria-live="polite">
          {pending
            ? "Vùng chọn chưa áp dụng. Dùng vùng đã chọn hoặc dùng toàn ảnh trước khi tìm."
            : image.data === image.url.split(",")[1]
              ? "Đang dùng toàn ảnh."
              : "Đang dùng vùng đã chọn."}
        </p>
      </div>
    </section>
  );
}
