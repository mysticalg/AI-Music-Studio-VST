const DEFAULT_REPOSITORY = {
  owner: "mysticalg",
  repo: "AI-Music-Studio-VST",
};

const catalogElement = document.querySelector("#catalog");
const emptyStateElement = document.querySelector("#empty-state");
const template = document.querySelector("#instrument-card-template");
const searchInput = document.querySelector("#catalog-search");
const repoNameElement = document.querySelector("#repo-name");
const releaseTagElement = document.querySelector("#release-tag");
const releaseNoteElement = document.querySelector("#release-note");
const releasesLinkElement = document.querySelector("#releases-link");
const instrumentCountElement = document.querySelector("#instrument-count");

let allInstruments = [];
let releaseAssetMap = new Map();

function detectRepository() {
  const hostname = window.location.hostname || "";
  const pathParts = window.location.pathname.split("/").filter(Boolean);
  const inferredOwner = hostname.endsWith(".github.io")
    ? hostname.replace(".github.io", "")
    : DEFAULT_REPOSITORY.owner;
  const inferredRepo = pathParts[0] || DEFAULT_REPOSITORY.repo;

  return {
    owner: inferredOwner,
    repo: inferredRepo,
  };
}

function releaseApiUrl(repository) {
  return `https://api.github.com/repos/${repository.owner}/${repository.repo}/releases?per_page=1`;
}

function releasePageUrl(repository) {
  return `https://github.com/${repository.owner}/${repository.repo}/releases`;
}

async function loadCatalog() {
  const response = await fetch("./data/instruments.json");
  if (!response.ok) {
    throw new Error("Failed to load instrument catalog.");
  }

  return response.json();
}

async function loadLatestRelease(repository) {
  const response = await fetch(releaseApiUrl(repository), {
    headers: {
      Accept: "application/vnd.github+json",
    },
  });

  if (!response.ok) {
    throw new Error("Failed to load GitHub release metadata.");
  }

  const releases = await response.json();
  return releases[0] ?? null;
}

function buildAssetMap(release) {
  const assets = release?.assets ?? [];
  return new Map(assets.map((asset) => [asset.name, asset.browser_download_url]));
}

function buildDownloadButton(linkElement, assetName, label) {
  const assetUrl = releaseAssetMap.get(assetName);
  linkElement.textContent = label;

  if (!assetUrl) {
    linkElement.classList.add("is-disabled");
    linkElement.removeAttribute("href");
    linkElement.removeAttribute("target");
    linkElement.removeAttribute("rel");
    return;
  }

  linkElement.classList.remove("is-disabled");
  linkElement.href = assetUrl;
  linkElement.target = "_blank";
  linkElement.rel = "noreferrer";
}

function buildCard(instrument) {
  const fragment = template.content.cloneNode(true);
  const card = fragment.querySelector(".instrument-card");
  const image = fragment.querySelector(".card-image");
  const family = fragment.querySelector(".family-badge");
  const name = fragment.querySelector(".instrument-name");
  const summary = fragment.querySelector(".instrument-summary");
  const tagRow = fragment.querySelector(".tag-row");
  const vst3Button = fragment.querySelector('[data-format="vst3"]');
  const standaloneButton = fragment.querySelector('[data-format="standalone"]');

  image.src = instrument.screenshot;
  image.alt = `${instrument.productName} screenshot`;
  image.addEventListener("error", () => {
    image.alt = `${instrument.productName} screenshot unavailable`;
    image.style.opacity = "0.2";
  });

  family.textContent = instrument.family;
  name.textContent = instrument.productName;
  summary.textContent = instrument.summary;

  instrument.tags.forEach((tag) => {
    const tagElement = document.createElement("span");
    tagElement.className = "tag";
    tagElement.textContent = tag;
    tagRow.appendChild(tagElement);
  });

  buildDownloadButton(vst3Button, instrument.releaseAssets.vst3, "Download VST3");
  buildDownloadButton(standaloneButton, instrument.releaseAssets.standalone, "Download Standalone");

  card.dataset.search = `${instrument.productName} ${instrument.family} ${instrument.summary} ${instrument.tags.join(" ")}`.toLowerCase();
  return fragment;
}

function renderCatalog(instruments) {
  catalogElement.innerHTML = "";

  instruments.forEach((instrument) => {
    catalogElement.appendChild(buildCard(instrument));
  });

  emptyStateElement.hidden = instruments.length > 0;
}

function applySearch() {
  const query = searchInput.value.trim().toLowerCase();
  const filtered = !query
    ? allInstruments
    : allInstruments.filter((instrument) => {
        const searchBlob = `${instrument.productName} ${instrument.family} ${instrument.summary} ${instrument.tags.join(" ")}`.toLowerCase();
        return searchBlob.includes(query);
      });

  renderCatalog(filtered);
}

function updateReleasePanel(repository, release) {
  repoNameElement.textContent = repository.repo;
  releasesLinkElement.href = releasePageUrl(repository);

  if (!release) {
    releaseTagElement.textContent = "No published release yet";
    releaseNoteElement.textContent =
      "Run the Release Bundled Instruments workflow to publish the ZIP assets for every VST3 and Standalone build.";
    return;
  }

  releaseTagElement.textContent = release.tag_name;
  releaseNoteElement.textContent = `Live assets loaded from the latest GitHub release. Published ${new Date(release.published_at).toLocaleDateString()}.`;
}

async function boot() {
  const repository = detectRepository();
  let release = null;

  try {
    [allInstruments, release] = await Promise.all([loadCatalog(), loadLatestRelease(repository)]);
    instrumentCountElement.textContent = String(allInstruments.length);
    releaseAssetMap = buildAssetMap(release);
    updateReleasePanel(repository, release);
    renderCatalog(allInstruments);
  } catch (error) {
    releaseTagElement.textContent = "GitHub metadata unavailable";
    releaseNoteElement.textContent =
      "The catalog still loaded locally, but GitHub release metadata could not be fetched right now.";

    try {
      allInstruments = await loadCatalog();
      instrumentCountElement.textContent = String(allInstruments.length);
      renderCatalog(allInstruments);
    } catch (catalogError) {
      catalogElement.innerHTML = `<p class="empty-state">Failed to load the instrument catalog.</p>`;
    }
  }

  searchInput.addEventListener("input", applySearch);
}

boot();
