const MODEL_URL = "https://justadudewhohacks.github.io/face-api.js/models";
const MAX_UPLOAD_BYTES = 8 * 1024 * 1024;

const elements = {
  dropzone: document.querySelector("#dropzone"),
  fileInput: document.querySelector("#file-input"),
  browseButton: document.querySelector("#browse-button"),
  replaceButton: document.querySelector("#replace-button"),
  emptyState: document.querySelector("#empty-state"),
  previewState: document.querySelector("#preview-state"),
  preview: document.querySelector("#preview"),
  fileMeta: document.querySelector("#file-meta"),
  verifyButton: document.querySelector("#verify-button"),
  modelStatus: document.querySelector("#model-status"),
  errorBox: document.querySelector("#error-box"),
  results: document.querySelector("#results"),
};

let selectedFile = null;
let modelsReady = false;
let previewUrl = null;

function showError(message) {
  elements.errorBox.textContent = message;
  elements.errorBox.hidden = false;
}

function clearError() {
  elements.errorBox.hidden = true;
  elements.errorBox.textContent = "";
}

function setStep(name, state, label) {
  const item = document.querySelector(`[data-step="${name}"]`);
  item.classList.remove("active", "complete", "error");
  if (state) item.classList.add(state);
  item.querySelector(".step-state").textContent = label;
}

function resetPipeline() {
  for (const name of ["encode", "search", "record"]) setStep(name, "", "Waiting");
  elements.results.hidden = true;
  clearError();
}

function openPicker(event) {
  event?.stopPropagation();
  elements.fileInput.click();
}

function selectFile(file) {
  clearError();
  if (!file || !/^image\/(jpeg|png|webp)$/.test(file.type)) return showError("Choose a JPG, PNG, or WebP image.");
  if (file.size > MAX_UPLOAD_BYTES) return showError("Choose an image smaller than 8 MB.");
  selectedFile = file;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(file);
  elements.preview.src = previewUrl;
  elements.emptyState.hidden = true;
  elements.previewState.hidden = false;
  elements.fileMeta.textContent = `${file.name} / ${(file.size / 1024).toFixed(0)} KB / processed locally`;
  elements.verifyButton.disabled = !modelsReady;
  resetPipeline();
}

async function loadModels() {
  try {
    if (!window.faceapi) throw new Error("Encoder library did not load.");
    await Promise.all([
      faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
      faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL),
      faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL),
    ]);
    modelsReady = true;
    elements.modelStatus.textContent = "Local encoder ready";
    elements.modelStatus.classList.add("ready");
    elements.verifyButton.disabled = !selectedFile;
  } catch {
    elements.modelStatus.textContent = "Encoder unavailable";
    showError("The local face encoder could not load. Check your connection and refresh the page.");
  }
}

async function hashDescriptor(descriptor) {
  const digest = await crypto.subtle.digest("SHA-256", descriptor.buffer);
  return [...new Uint8Array(digest)].map((value) => value.toString(16).padStart(2, "0")).join("");
}

async function prepareUpload(image) {
  const maxSide = 1000;
  const ratio = Math.min(1, maxSide / Math.max(image.naturalWidth, image.naturalHeight));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(image.naturalWidth * ratio);
  canvas.height = Math.round(image.naturalHeight * ratio);
  canvas.getContext("2d", { alpha: false }).drawImage(image, 0, 0, canvas.width, canvas.height);

  let quality = .82;
  let dataUrl = canvas.toDataURL("image/jpeg", quality);
  while (Math.ceil((dataUrl.length - dataUrl.indexOf(",") - 1) * .75) > 480 * 1024 && quality > .4) {
    quality -= .1;
    dataUrl = canvas.toDataURL("image/jpeg", quality);
  }
  return dataUrl;
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || "The request could not be completed.");
  return payload;
}

async function verify() {
  if (!selectedFile || !modelsReady) return;
  resetPipeline();
  elements.verifyButton.disabled = true;
  elements.verifyButton.querySelector("span:first-child").textContent = "Verification running";
  elements.dropzone.classList.add("is-scanning");

  try {
    setStep("encode", "active", "Scanning");
    const detection = await faceapi
      .detectSingleFace(elements.preview, new faceapi.TinyFaceDetectorOptions({ inputSize: 416, scoreThreshold: .45 }))
      .withFaceLandmarks()
      .withFaceDescriptor();
    if (!detection) throw new Error("No clear face was detected. Try a front-facing, well-lit image.");
    const faceHash = await hashDescriptor(detection.descriptor);
    setStep("encode", "complete", "Encoded");

    setStep("search", "active", "Searching");
    const image = await prepareUpload(elements.preview);
    const match = await postJson("/api/search", { image });
    setStep("search", "complete", "Match found");

    setStep("record", "active", "Confirming");
    const chain = await postJson("/api/record", { faceHash, matchedUrl: match.url });
    setStep("record", "complete", "Anchored");
    renderResults(faceHash, match, chain);
  } catch (error) {
    const active = document.querySelector(".pipeline-item.active");
    if (active) {
      active.classList.remove("active");
      active.classList.add("error");
      active.querySelector(".step-state").textContent = "Failed";
    }
    showError(error.message || "Verification failed. Please try again.");
  } finally {
    elements.dropzone.classList.remove("is-scanning");
    elements.verifyButton.disabled = false;
    elements.verifyButton.querySelector("span:first-child").textContent = "Run verification";
  }
}

function renderResults(faceHash, match, chain) {
  document.querySelector("#face-hash").textContent = faceHash;
  document.querySelector("#match-title").textContent = match.title;
  const matchLink = document.querySelector("#match-link");
  matchLink.href = match.url;
  matchLink.textContent = match.domain;
  document.querySelector("#record-id").textContent = chain.recordId ?? "Confirmed";
  document.querySelector("#block-number").textContent = chain.blockNumber;
  document.querySelector("#tx-short").textContent = `${chain.txHash.slice(0, 8)}...${chain.txHash.slice(-6)}`;
  document.querySelector("#explorer-link").href = chain.explorerUrl;
  document.querySelector("#completed-at").textContent = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date());
  elements.results.hidden = false;
  elements.results.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
}

elements.browseButton.addEventListener("click", openPicker);
elements.replaceButton.addEventListener("click", openPicker);
elements.dropzone.addEventListener("click", (event) => {
  if (!event.target.closest("button")) openPicker(event);
});
elements.dropzone.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    openPicker(event);
  }
});
elements.fileInput.addEventListener("change", () => selectFile(elements.fileInput.files[0]));
for (const eventName of ["dragenter", "dragover"]) {
  elements.dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropzone.classList.add("is-dragging");
  });
}
for (const eventName of ["dragleave", "drop"]) {
  elements.dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropzone.classList.remove("is-dragging");
  });
}
elements.dropzone.addEventListener("drop", (event) => selectFile(event.dataTransfer.files[0]));
elements.verifyButton.addEventListener("click", verify);
document.querySelector("[data-copy='face-hash']").addEventListener("click", async (event) => {
  await navigator.clipboard.writeText(document.querySelector("#face-hash").textContent);
  event.currentTarget.textContent = "Fingerprint copied";
  setTimeout(() => { event.currentTarget.textContent = "Copy fingerprint"; }, 1600);
});

window.addEventListener("load", loadModels, { once: true });
