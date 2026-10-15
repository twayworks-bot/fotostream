/**
 * Main Application Dashboard Script for FOTOSTREAM
 */

let selectedFiles = [];
const MAX_IMAGES = 49;
let activePollInterval = null;

document.addEventListener("DOMContentLoaded", () => {
  const prefix = window.FOTOSTREAM_PREFIX || "fotostream";

  initDragAndDrop();
  initBgmSelector(prefix);
  initResolutionSelector();
  loadSystemStatus(prefix);
  loadRecentJobs(prefix);
  loadVideos(prefix);

  // Poll system status and active jobs every 3 seconds
  setInterval(() => {
    loadSystemStatus(prefix);
    loadRecentJobs(prefix);
  }, 3000);

  // Form Submission
  const uploadForm = document.getElementById("synthesisForm");
  if (uploadForm) {
    uploadForm.addEventListener("submit", (e) => {
      e.preventDefault();
      handleFormSubmit(prefix);
    });
  }
});

function initResolutionSelector() {
  const radios = document.querySelectorAll("input[name='video_resolution']");
  radios.forEach(radio => {
    radio.addEventListener("change", () => {
      radios.forEach(r => {
        const parent = r.closest("label");
        if (parent) {
          parent.classList.remove("border-2", "border-indigo-500", "bg-indigo-950/40", "ring-1", "ring-indigo-500/50");
          parent.classList.add("border", "border-slate-700", "bg-slate-900/60");
        }
      });
      const activeParent = radio.closest("label");
      if (activeParent) {
        activeParent.classList.remove("border", "border-slate-700", "bg-slate-900/60");
        activeParent.classList.add("border-2", "border-indigo-500", "bg-indigo-950/40", "ring-1", "ring-indigo-500/50");
      }
    });
  });
}

function initDragAndDrop() {
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("imageFileInput");

  if (!dropZone || !fileInput) return;

  dropZone.addEventListener("click", () => fileInput.click());

  ["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.add("border-indigo-500", "bg-slate-800/80");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.remove("border-indigo-500", "bg-slate-800/80");
    });
  });

  dropZone.addEventListener("drop", (e) => {
    const files = Array.from(e.dataTransfer.files);
    addImages(files);
  });

  fileInput.addEventListener("change", (e) => {
    const files = Array.from(e.target.files);
    addImages(files);
    fileInput.value = ""; // reset for next trigger
  });
}

function addImages(files) {
  const validFiles = files.filter(f => f.type.startsWith("image/"));
  const remainingSlots = MAX_IMAGES - selectedFiles.length;

  if (validFiles.length > remainingSlots) {
    alert(`최대 ${MAX_IMAGES}장까지만 업로드할 수 있습니다. (현재 선택 가능: ${remainingSlots}장)`);
  }

  const filesToAdd = validFiles.slice(0, remainingSlots);
  selectedFiles = selectedFiles.concat(filesToAdd);
  updateImagePreviewGrid();
}

function removeImage(index) {
  selectedFiles.splice(index, 1);
  updateImagePreviewGrid();
}

function clearAllImages() {
  selectedFiles = [];
  updateImagePreviewGrid();
}

function updateImagePreviewGrid() {
  const countBadge = document.getElementById("selectedCountBadge");
  const gridContainer = document.getElementById("previewGrid");
  const clearBtn = document.getElementById("clearImagesBtn");

  if (countBadge) countBadge.textContent = `${selectedFiles.length} / ${MAX_IMAGES}`;
  if (clearBtn) clearBtn.style.display = selectedFiles.length > 0 ? "inline-block" : "none";

  if (!gridContainer) return;

  if (selectedFiles.length === 0) {
    gridContainer.innerHTML = "";
    gridContainer.classList.add("hidden");
    return;
  }

  gridContainer.classList.remove("hidden");
  gridContainer.innerHTML = selectedFiles.map((file, idx) => {
    const objectUrl = URL.createObjectURL(file);
    return `
      <div class="relative group aspect-square rounded-md overflow-hidden bg-slate-800 border border-slate-700">
        <img src="${objectUrl}" class="w-full h-full object-cover" onload="URL.revokeObjectURL('${objectUrl}')" />
        <span class="absolute top-1 left-1 bg-black/60 text-white text-[10px] px-1 rounded font-mono">${idx + 1}</span>
        <button 
          type="button" 
          onclick="removeImage(${idx})"
          class="absolute top-1 right-1 w-5 h-5 bg-rose-600/80 hover:bg-rose-600 text-white rounded-full flex items-center justify-center text-xs opacity-0 group-hover:opacity-100 transition-opacity"
        >×</button>
      </div>
    `;
  }).join("");
}

async function handleFormSubmit(prefix) {
  if (selectedFiles.length === 0) {
    alert("동영상으로 제작할 사진을 최소 1장 이상 등록해주세요.");
    return;
  }

  const titleInput = document.getElementById("videoTitle");
  const submitBtn = document.getElementById("submitJobBtn");
  const statusMsg = document.getElementById("formStatusMsg");

  const formData = new FormData();
  formData.append("title", titleInput.value.trim() || "My Photo Slideshow");

  // Attach images
  selectedFiles.forEach((file) => {
    formData.append("images", file);
  });

  // Attach resolution
  const resChoice = document.querySelector("input[name='video_resolution']:checked")?.value || "1080p";
  formData.append("resolution", resChoice);

  // Attach BGM choice
  const bgmChoice = document.querySelector("input[name='bgm_option']:checked")?.value || "library";
  if (bgmChoice === "library" && typeof selectedBgmId !== "undefined" && selectedBgmId) {
    formData.append("bgm_id", selectedBgmId);
  } else if (bgmChoice === "custom") {
    const customFileInput = document.getElementById("customBgmFile");
    if (customFileInput && customFileInput.files.length > 0) {
      formData.append("bgm_file", customFileInput.files[0]);
    }
  }

  try {
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span class="inline-block animate-spin mr-2">⟳</span> 작업 큐 등록 중...`;
    statusMsg.textContent = "이미지 전송 및 작업 큐 등록 중...";
    statusMsg.className = "text-sm text-indigo-400 mt-2";

    const res = await fetch(`/${prefix}/api/v1/jobs`, {
      method: "POST",
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "작업 요청 실패");
    }

    const data = await res.json();
    statusMsg.textContent = `작업이 큐에 등록되었습니다! (Job ID: ${data.job_id.slice(0, 8)})`;
    statusMsg.className = "text-sm text-emerald-400 mt-2";

    // Reset upload state
    clearAllImages();
    titleInput.value = "";

    // Trigger immediate reload of jobs and status
    loadRecentJobs(prefix);
    loadSystemStatus(prefix);

  } catch (err) {
    statusMsg.textContent = `오류 발생: ${err.message}`;
    statusMsg.className = "text-sm text-rose-400 mt-2";
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `동영상 생성 큐 등록 (합성 시작)`;
  }
}

async function loadSystemStatus(prefix) {
  try {
    const res = await fetch(`/${prefix}/api/v1/system/status`);
    if (!res.ok) return;
    const data = await res.json();

    const workerStat = document.getElementById("workerStatBadge");
    const streamStat = document.getElementById("streamStatBadge");
    const ffmpegStat = document.getElementById("ffmpegStatBadge");

    if (workerStat) {
      workerStat.textContent = `${data.workers.active} / ${data.workers.max}`;
      workerStat.className = data.workers.active > 0 ? "font-bold text-amber-400" : "font-bold text-slate-300";
    }

    if (streamStat) {
      streamStat.textContent = `${data.streams.active} / ${data.streams.max}`;
      streamStat.className = data.streams.active >= 8 ? "font-bold text-rose-400" : "font-bold text-slate-300";
    }

    if (ffmpegStat) {
      ffmpegStat.textContent = data.ffmpeg_available ? "정상 연결" : "미확인 (확인 필요)";
      ffmpegStat.className = data.ffmpeg_available ? "text-emerald-400 font-medium" : "text-rose-400 font-medium";
    }
  } catch (err) {
    console.warn("Could not load system status:", err);
  }
}

async function loadRecentJobs(prefix) {
  const container = document.getElementById("jobsContainer");
  if (!container) return;

  try {
    const res = await fetch(`/${prefix}/api/v1/jobs?limit=5`);
    if (!res.ok) return;
    const data = await res.json();

    const jobs = data.jobs || [];
    if (jobs.length === 0) {
      container.innerHTML = `<div class="p-4 text-center text-slate-500 text-sm">현재 대기 중이거나 진행 중인 작업이 없습니다.</div>`;
      return;
    }

    container.innerHTML = jobs.map(j => {
      let statusBadge = "";
      if (j.status === "QUEUED") {
        statusBadge = `<span class="px-2 py-0.5 rounded text-xs bg-amber-500/20 text-amber-300 border border-amber-500/30">대기 중 (Queued)</span>`;
      } else if (j.status === "PROCESSING") {
        statusBadge = `<span class="px-2 py-0.5 rounded text-xs bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center gap-1.5"><span class="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse"></span>합성 중 (${j.progress}%)</span>`;
      } else if (j.status === "COMPLETED") {
        statusBadge = `<span class="px-2 py-0.5 rounded text-xs bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">완료</span>`;
      } else {
        statusBadge = `<span class="px-2 py-0.5 rounded text-xs bg-rose-500/20 text-rose-300 border border-rose-500/30">실패</span>`;
      }

      const isCompleted = j.status === "COMPLETED";

      return `
        <div class="p-3 bg-slate-800/40 rounded-lg border border-slate-700/60 flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div class="flex-1">
            <div class="flex items-center gap-2">
              <span class="font-medium text-slate-200">${escapeHtml(j.title)}</span>
              ${statusBadge}
            </div>
            <div class="text-xs text-slate-400 mt-1 flex items-center gap-3">
              <span>사진: ${j.image_count}장 (${j.grid_rows}x${j.grid_cols})</span>
              <span>•</span>
              <span>등록: ${new Date(j.created_at).toLocaleTimeString()}</span>
              ${j.error_message ? `<span class="text-rose-400 truncate max-w-xs">• ${escapeHtml(j.error_message)}</span>` : ''}
            </div>

            ${j.status === "PROCESSING" ? `
              <div class="w-full bg-slate-700 rounded-full h-1.5 mt-2 overflow-hidden">
                <div class="bg-indigo-500 h-1.5 rounded-full transition-all duration-300" style="width: ${j.progress}%"></div>
              </div>
            ` : ''}
          </div>

          <div class="flex items-center gap-2">
            ${isCompleted && j.stream_url ? `
              <button 
                onclick="openVideoModal('${prefix}', '${j.video_id}', '${escapeHtml(j.title)}', '${j.stream_url}', '${j.resolution || ''}')"
                class="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-medium transition-colors flex items-center gap-1"
              >
                <span>▶</span> 스트리밍 재생
              </button>
            ` : ''}
            ${j.status === "QUEUED" || j.status === "PROCESSING" ? `
              <button 
                onclick="cancelJob('${prefix}', '${j.id}')"
                class="px-2.5 py-1.5 bg-slate-700 hover:bg-rose-600/80 text-slate-300 hover:text-white rounded text-xs transition-colors"
              >
                취소
              </button>
            ` : ''}
          </div>
        </div>
      `;
    }).join("");

    // If any jobs completed, refresh video gallery
    if (jobs.some(j => j.status === "COMPLETED")) {
      loadVideos(prefix);
    }
  } catch (err) {
    console.warn("Could not load jobs:", err);
  }
}

async function cancelJob(prefix, jobId) {
  if (!confirm("해당 작업을 취소하시겠습니까?")) return;
  try {
    await fetch(`/${prefix}/api/v1/jobs/${jobId}`, { method: "DELETE" });
    loadRecentJobs(prefix);
  } catch (err) {
    alert("작업 취소 실패: " + err.message);
  }
}

async function loadVideos(prefix) {
  const container = document.getElementById("videosGallery");
  if (!container) return;

  try {
    const res = await fetch(`/${prefix}/api/v1/videos?limit=20`);
    if (!res.ok) return;
    const data = await res.json();
    const videos = data.videos || [];

    if (videos.length === 0) {
      container.innerHTML = `
        <div class="col-span-full py-12 text-center text-slate-500">
          <p class="text-base">아직 생성된 동영상이 없습니다.</p>
          <p class="text-xs mt-1">상단의 사진 업로드 영역에서 최대 49장의 사진을 올려 첫 영상을 만들어보세요!</p>
        </div>
      `;
      return;
    }

    container.innerHTML = videos.map(v => {
      const isVert = isVerticalResolution(v.resolution);
      return `
        <div class="glass-panel glass-panel-hover rounded-xl overflow-hidden flex flex-col transition-all duration-200">
          <div class="relative ${isVert ? 'aspect-[9/16] max-h-72 mx-auto w-full' : 'aspect-video'} bg-black/60 group cursor-pointer" onclick="openVideoModal('${prefix}', '${v.id}', '${escapeHtml(v.title)}', '${v.stream_url}', '${v.resolution || ''}')">
            ${v.thumbnail_url ? `
              <img src="${v.thumbnail_url}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
            ` : `
              <div class="w-full h-full flex items-center justify-center text-slate-600 font-mono text-xs">No Thumbnail</div>
            `}
            <div class="absolute inset-0 bg-black/30 group-hover:bg-black/10 transition-colors flex items-center justify-center">
              <div class="w-12 h-12 rounded-full bg-indigo-600/90 text-white flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
                ▶
              </div>
            </div>
            ${isVert ? `
              <span class="absolute top-2 left-2 bg-purple-600/90 text-white text-[10px] px-1.5 py-0.5 rounded font-bold tracking-wider shadow">
                9:16 Shorts
              </span>
            ` : ''}
            <span class="absolute bottom-2 right-2 bg-black/80 text-white text-[10px] px-1.5 py-0.5 rounded font-mono">
              ${v.duration_formatted || '00:00'}
            </span>
          </div>

          <div class="p-3.5 flex-1 flex flex-col justify-between">
            <div>
              <h4 class="font-semibold text-slate-100 text-sm truncate" title="${escapeHtml(v.title)}">${escapeHtml(v.title)}</h4>
              <div class="flex items-center gap-2 text-xs text-slate-400 mt-1">
                <span class="px-1.5 py-0.2 rounded ${isVert ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30' : 'bg-indigo-500/20 text-indigo-300'} font-mono text-[11px]">${v.resolution || '1080p'}</span>
                <span>•</span>
                <span>${v.file_size_formatted || '0 MB'}</span>
                <span>•</span>
                <span>조회 ${v.view_count}회</span>
              </div>
            </div>

            <div class="mt-3 pt-2.5 border-t border-slate-700/60 flex items-center justify-between text-xs">
              <button 
                type="button"
                onclick="copyStreamUrl('${v.stream_url}')"
                class="text-indigo-400 hover:text-indigo-300 font-medium"
              >
                URL 복사
              </button>
              <div class="flex items-center gap-2">
                <a 
                  href="/${prefix}/api/v1/videos/${v.id}/download" 
                  download 
                  class="text-slate-300 hover:text-white"
                  title="다운로드"
                >
                  다운로드
                </a>
                <button 
                  type="button" 
                  onclick="deleteVideo('${prefix}', '${v.id}')"
                  class="text-rose-400 hover:text-rose-300"
                  title="삭제"
                >
                  삭제
                </button>
              </div>
            </div>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    console.warn("Could not load videos:", err);
  }
}

function isVerticalResolution(resolution) {
  if (!resolution) return false;
  const parts = resolution.toLowerCase().split("x");
  if (parts.length === 2) {
    const w = parseInt(parts[0], 10);
    const h = parseInt(parts[1], 10);
    if (!isNaN(w) && !isNaN(h)) {
      return w < h;
    }
  }
  return false;
}

function applyModalAspect(isVertical) {
  const card = document.getElementById("videoModalCard");
  const wrapper = document.getElementById("videoPlayerWrapper");
  if (!card || !wrapper) return;

  if (isVertical) {
    // 9:16 Vertical Video Preview (Shorts / Reels style)
    card.classList.remove("max-w-3xl");
    card.classList.add("max-w-sm"); // ~384px width, perfectly proportioned for mobile vertical video
    wrapper.style.aspectRatio = "9 / 16";
    wrapper.style.maxHeight = "78vh";
    wrapper.style.width = "100%";
  } else {
    // 16:9 Widescreen Video Preview
    card.classList.remove("max-w-sm");
    card.classList.add("max-w-3xl"); // 768px width
    wrapper.style.aspectRatio = "16 / 9";
    wrapper.style.maxHeight = "70vh";
    wrapper.style.width = "100%";
  }
}

function openVideoModal(prefix, videoId, title, streamUrl, resolution) {
  const modal = document.getElementById("videoPlayerModal");
  const modalTitle = document.getElementById("playerModalTitle");
  const videoPlayer = document.getElementById("mainVideoPlayer");
  const urlDisplay = document.getElementById("streamUrlInput");

  if (!modal || !videoPlayer) return;

  const fullStreamUrl = window.location.origin + streamUrl;

  modalTitle.textContent = title;
  videoPlayer.src = streamUrl;
  urlDisplay.value = fullStreamUrl;

  // Set aspect ratio from resolution metadata immediately
  applyModalAspect(isVerticalResolution(resolution));

  // Also verify and adjust based on actual stream dimensions when loaded
  videoPlayer.onloadedmetadata = () => {
    if (videoPlayer.videoWidth > 0 && videoPlayer.videoHeight > 0) {
      applyModalAspect(videoPlayer.videoWidth < videoPlayer.videoHeight);
    }
  };

  modal.classList.remove("hidden");
  videoPlayer.play().catch(e => console.warn("Autoplay blocked:", e));
}

function closeVideoModal() {
  const modal = document.getElementById("videoPlayerModal");
  const videoPlayer = document.getElementById("mainVideoPlayer");
  if (videoPlayer) {
    videoPlayer.pause();
    videoPlayer.src = "";
  }
  if (modal) modal.classList.add("hidden");
}

function copyStreamUrl(streamUrl) {
  const fullUrl = window.location.origin + streamUrl;
  navigator.clipboard.writeText(fullUrl).then(() => {
    alert("스트리밍 엔드포인트 URL이 클립보드에 복사되었습니다:\n" + fullUrl);
  }).catch(() => {
    prompt("스트리밍 URL:", fullUrl);
  });
}

async function deleteVideo(prefix, videoId) {
  if (!confirm("이 동영상을 삭제하시겠습니까?")) return;
  try {
    const res = await fetch(`/${prefix}/api/v1/videos/${videoId}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Delete failed");
    loadVideos(prefix);
    loadSystemStatus(prefix);
  } catch (err) {
    alert("삭제 실패: " + err.message);
  }
}
