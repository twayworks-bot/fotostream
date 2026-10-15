/**
 * BGM Selector & Audio Preview Module
 */

let currentAudio = new Audio();
let currentlyPlayingTrackId = null;
let selectedBgmId = null;

function initBgmSelector(prefix) {
  loadBgmTracks(prefix);

  // Stop audio when page closes or modal closes
  window.addEventListener("beforeunload", () => {
    if (currentAudio) currentAudio.pause();
  });

  // Admin BGM Upload Form submission
  const uploadForm = document.getElementById("adminBgmForm");
  if (uploadForm) {
    uploadForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      await handleAdminBgmUpload(prefix);
    });
  }
}

async function loadBgmTracks(prefix) {
  const container = document.getElementById("bgmListContainer");
  if (!container) return;

  try {
    const res = await fetch(`/${prefix}/api/v1/bgm`);
    const data = await res.json();
    renderBgmCards(prefix, data.tracks || []);
  } catch (err) {
    console.error("Failed to load BGM tracks:", err);
    container.innerHTML = `<p class="text-rose-400 text-sm">BGM 목록을 불러오는 중 오류가 발생했습니다.</p>`;
  }
}

function renderBgmCards(prefix, tracks) {
  const container = document.getElementById("bgmListContainer");
  if (!container) return;

  if (tracks.length === 0) {
    selectedBgmId = null;
    container.innerHTML = `<p class="text-slate-400 text-sm">등록된 BGM 음원이 없습니다. 관리자가 상단의 '+ BGM 등록'을 통해 음원을 추가할 수 있습니다.</p>`;
    return;
  }

  if (!selectedBgmId || !tracks.some(t => t.id === selectedBgmId)) {
    selectedBgmId = tracks[0].id;
  }

  container.innerHTML = tracks.map((track) => {
    const isSelected = selectedBgmId === track.id;
    const isPlaying = currentlyPlayingTrackId === track.id;
    const durMin = Math.floor(track.duration / 60);
    const durSec = Math.floor(track.duration % 60).toString().padStart(2, "0");

    return `
      <div 
        id="bgm-card-${track.id}"
        class="bgm-card relative p-3 rounded-lg border transition-all cursor-pointer flex items-center justify-between ${
          isSelected ? 'border-indigo-500 bg-indigo-950/40 ring-1 ring-indigo-500' : 'border-slate-700/60 bg-slate-800/40 hover:border-slate-600'
        }"
        onclick="selectBgmTrack('${track.id}')"
      >
        <div class="flex items-center gap-3">
          <button 
            type="button"
            onclick="event.stopPropagation(); toggleBgmPlay('${prefix}', '${track.id}', '${track.stream_url}')"
            class="w-9 h-9 rounded-full flex items-center justify-center transition-colors ${
              isPlaying ? 'bg-indigo-500 text-white' : 'bg-slate-700 hover:bg-slate-600 text-slate-200'
            }"
            title="${isPlaying ? '정지' : '미리듣기'}"
          >
            <span id="play-icon-${track.id}">${isPlaying ? '■' : '▶'}</span>
          </button>
          <div>
            <div class="flex items-center gap-2">
              <span class="text-sm font-medium text-slate-100">${escapeHtml(track.title)}</span>
              ${track.is_preset ? '<span class="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">기본 추천</span>' : ''}
              <span class="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">${escapeHtml(track.mood)}</span>
            </div>
            <div class="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
              <span>${escapeHtml(track.artist)}</span>
              <span>•</span>
              <span>${durMin}:${durSec}</span>
              <span>•</span>
              <span class="text-emerald-400 text-[11px]">${escapeHtml(track.source)}</span>
            </div>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <button 
            type="button"
            onclick="event.stopPropagation(); deleteBgmTrack('${prefix}', '${track.id}', '${escapeHtml(track.title)}')"
            class="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
            title="BGM 삭제"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
          <input 
            type="radio" 
            name="selected_bgm" 
            value="${track.id}" 
            ${isSelected ? 'checked' : ''} 
            class="text-indigo-600 focus:ring-indigo-500 h-4 w-4"
            onclick="event.stopPropagation(); selectBgmTrack('${track.id}')"
          />
        </div>
      </div>
    `;
  }).join("");
}

async function deleteBgmTrack(prefix, trackId, trackTitle) {
  if (!confirm(`'${trackTitle}' 음원을 라이브러리에서 삭제하시겠습니까?`)) {
    return;
  }

  try {
    if (currentlyPlayingTrackId === trackId) {
      currentAudio.pause();
      currentlyPlayingTrackId = null;
      updatePlayIcons(null);
    }

    const clean = prefix ? prefix.replace(/^\/+/, '').replace(/\/+$/, '') : '';
    const url = clean ? `/${clean}/api/v1/bgm/${trackId}` : `/api/v1/bgm/${trackId}`;

    const res = await fetch(url, {
      method: "DELETE"
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "삭제에 실패했습니다.");
    }

    if (selectedBgmId === trackId) {
      selectedBgmId = null;
    }

    await loadBgmTracks(prefix);
  } catch (err) {
    alert(`BGM 삭제 오류: ${err.message}`);
  }
}

function selectBgmTrack(trackId) {
  selectedBgmId = trackId;
  document.querySelectorAll(".bgm-card").forEach(el => {
    el.classList.remove("border-indigo-500", "bg-indigo-950/40", "ring-1", "ring-indigo-500");
    el.classList.add("border-slate-700/60", "bg-slate-800/40");
  });

  const target = document.getElementById(`bgm-card-${trackId}`);
  if (target) {
    target.classList.add("border-indigo-500", "bg-indigo-950/40", "ring-1", "ring-indigo-500");
    const radio = target.querySelector("input[type=radio]");
    if (radio) radio.checked = true;
  }
}

function toggleBgmPlay(prefix, trackId, streamUrl) {
  if (currentlyPlayingTrackId === trackId) {
    currentAudio.pause();
    currentlyPlayingTrackId = null;
    updatePlayIcons(null);
  } else {
    currentAudio.pause();
    currentAudio.src = streamUrl;
    currentAudio.play().catch(e => console.error("Audio playback error:", e));
    currentlyPlayingTrackId = trackId;
    updatePlayIcons(trackId);
  }

  currentAudio.onended = () => {
    currentlyPlayingTrackId = null;
    updatePlayIcons(null);
  };
}

function updatePlayIcons(playingId) {
  document.querySelectorAll("[id^='play-icon-']").forEach(icon => {
    icon.textContent = "▶";
  });
  if (playingId) {
    const active = document.getElementById(`play-icon-${playingId}`);
    if (active) active.textContent = "■";
  }
}

async function handleAdminBgmUpload(prefix) {
  const fileInput = document.getElementById("adminBgmFile");
  const titleInput = document.getElementById("adminBgmTitle");
  const artistInput = document.getElementById("adminBgmArtist");
  const moodInput = document.getElementById("adminBgmMood");
  const sourceInput = document.getElementById("adminBgmSource");
  const licenseInput = document.getElementById("adminBgmLicense");
  const statusMsg = document.getElementById("adminBgmStatusMsg");

  if (!fileInput.files || fileInput.files.length === 0) {
    statusMsg.textContent = "오디오 파일을 선택해주세요.";
    statusMsg.className = "text-xs text-rose-400 mt-2";
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  formData.append("title", titleInput.value.trim());
  formData.append("artist", artistInput.value.trim());
  formData.append("mood", moodInput.value);
  formData.append("source", sourceInput.value.trim() || "Pixabay Music");
  formData.append("license_info", licenseInput.value.trim() || "Free for Commercial Use");

  try {
    statusMsg.textContent = "음원 업로드 및 분석 중...";
    statusMsg.className = "text-xs text-indigo-400 mt-2";

    const res = await fetch(`/${prefix}/api/v1/bgm`, {
      method: "POST",
      body: formData
    });

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || "Upload failed");
    }

    const createdTrack = await res.json();
    statusMsg.textContent = "BGM 등록 완료!";
    statusMsg.className = "text-xs text-emerald-400 mt-2";

    // Reset inputs and reload list
    fileInput.value = "";
    titleInput.value = "";
    artistInput.value = "";
    setTimeout(() => {
      closeAdminBgmModal();
      loadBgmTracks(prefix);
      selectBgmTrack(createdTrack.id);
    }, 800);
  } catch (err) {
    statusMsg.textContent = `등록 오류: ${err.message}`;
    statusMsg.className = "text-xs text-rose-400 mt-2";
  }
}

function openAdminBgmModal() {
  const modal = document.getElementById("adminBgmModal");
  if (modal) modal.classList.remove("hidden");
}

function closeAdminBgmModal() {
  const modal = document.getElementById("adminBgmModal");
  if (modal) modal.classList.add("hidden");
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
