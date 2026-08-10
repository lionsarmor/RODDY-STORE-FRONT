function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error("Could not read that file."));
    reader.readAsDataURL(file);
  });
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("That file isn't a readable image."));
    img.src = src;
  });
}

/** Resizes to at most `maxDim` on the long edge and re-encodes as JPEG, so
    committed product photos stay small and always land on the same
    filename/extension regardless of what was uploaded. */
export async function compressImage(file, { maxDim = 1000, quality = 0.82 } = {}) {
  const raw = await readFileAsDataUrl(file);
  const img = await loadImage(raw);

  const scale = Math.min(1, maxDim / Math.max(img.width, img.height));
  const width = Math.max(1, Math.round(img.width * scale));
  const height = Math.max(1, Math.round(img.height * scale));

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#ffffff"; // flattens transparency instead of going black
  ctx.fillRect(0, 0, width, height);
  ctx.drawImage(img, 0, 0, width, height);

  return canvas.toDataURL("image/jpeg", quality);
}

export function dataUrlToBase64(dataUrl) {
  return dataUrl.slice(dataUrl.indexOf(",") + 1);
}
