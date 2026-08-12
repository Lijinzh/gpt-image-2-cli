const menuButton = document.querySelector('[data-menu-button]');
const siteNav = document.querySelector('[data-site-nav]');
const toast = document.querySelector('[data-copy-toast]');
let toastTimer;

function showToast(message = '已复制到剪贴板') {
  toast.textContent = message;
  toast.classList.add('is-visible');
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove('is-visible'), 1800);
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    textarea.remove();
  }
  showToast();
}

document.querySelectorAll('[data-copy-target]').forEach((button) => {
  button.addEventListener('click', () => {
    const target = document.getElementById(button.dataset.copyTarget);
    if (target) copyText(target.textContent.trim());
  });
});

menuButton?.addEventListener('click', () => {
  const isOpen = siteNav.classList.toggle('is-open');
  menuButton.setAttribute('aria-expanded', String(isOpen));
});

siteNav?.querySelectorAll('a').forEach((link) => {
  link.addEventListener('click', () => {
    siteNav.classList.remove('is-open');
    menuButton?.setAttribute('aria-expanded', 'false');
  });
});

const feedbackDialog = document.querySelector('[data-feedback-dialog]');
const feedbackForm = document.querySelector('[data-feedback-form]');
const feedbackPreview = document.querySelector('[data-feedback-preview]');
const feedbackCategory = document.querySelector('[data-feedback-category]');
const feedbackSubject = document.querySelector('[data-feedback-subject]');
const feedbackDetails = document.querySelector('[data-feedback-details]');
const feedbackSteps = document.querySelector('[data-feedback-steps]');
const feedbackEnvironment = document.querySelector('[data-feedback-environment]');
const feedbackIssueBase = 'https://github.com/Lijinzh/gpt-image-2-cli/issues/new';

function feedbackDraft() {
  const category = feedbackCategory?.selectedOptions[0]?.textContent.trim() || '其他意见';
  const subject = feedbackSubject?.value.trim() || '请填写一句话标题';
  const details = feedbackDetails?.value.trim() || '请填写详细说明';
  const steps = feedbackSteps?.value.trim() || '未提供';
  const environment = feedbackEnvironment?.value.trim() || '未提供';
  const body = [
    '<!-- website-feedback -->',
    '## 反馈类型',
    category,
    '',
    '## 详细说明',
    details,
    '',
    '## 操作步骤或上下文',
    steps,
    '',
    '## 使用环境',
    environment,
    '',
    '---',
    '通过 GPT-Image 2 CLI 项目网页整理。请勿在公开 Issue 中粘贴 API Key 或其他敏感信息。',
  ].join('\n');
  return { title: `[Website Feedback] ${subject}`, body };
}

function updateFeedbackPreview() {
  if (!feedbackPreview) return;
  const draft = feedbackDraft();
  feedbackPreview.textContent = `${draft.title}\n\n${draft.body}`;
}

document.querySelectorAll('[data-feedback-open]').forEach((button) => {
  button.addEventListener('click', () => {
    if (typeof feedbackDialog?.showModal === 'function') feedbackDialog.showModal();
    else feedbackDialog?.setAttribute('open', '');
    updateFeedbackPreview();
    window.setTimeout(() => feedbackSubject?.focus(), 80);
  });
});

document.querySelector('[data-feedback-close]')?.addEventListener('click', () => feedbackDialog?.close());
feedbackDialog?.addEventListener('click', (event) => {
  if (event.target === feedbackDialog) feedbackDialog.close();
});

[feedbackCategory, feedbackSubject, feedbackDetails, feedbackSteps, feedbackEnvironment].forEach(
  (control) => control?.addEventListener('input', updateFeedbackPreview),
);

document.querySelector('[data-feedback-copy]')?.addEventListener('click', () => {
  const draft = feedbackDraft();
  copyText(`${draft.title}\n\n${draft.body}`);
});

feedbackForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const draft = feedbackDraft();
  const issueUrl = new URL(feedbackIssueBase);
  issueUrl.searchParams.set('title', draft.title);
  issueUrl.searchParams.set('body', draft.body);
  if (issueUrl.toString().length > 7000) {
    await copyText(`${draft.title}\n\n${draft.body}`);
    issueUrl.searchParams.set(
      'body',
      '反馈内容较长，网页已经把完整内容复制到剪贴板。请在这里按 Ctrl+V（macOS 使用 Command+V）粘贴。',
    );
  }
  window.location.assign(issueUrl.toString());
});

updateFeedbackPreview();

const promptInput = document.querySelector('[data-prompt]');
const sizeInput = document.querySelector('[data-size]');
const qualityInput = document.querySelector('[data-quality]');
const commandOutput = document.querySelector('[data-command-output]');

function updateCommand() {
  const prompt = promptInput.value.trim().replaceAll('"', '\\"') || '你的提示词';
  commandOutput.textContent = `gpt-image generate "${prompt}" --size ${sizeInput.value} --quality ${qualityInput.value} -o .\\artifacts\\result.png`;
}

[promptInput, sizeInput, qualityInput].forEach((control) => control?.addEventListener('input', updateCommand));
updateCommand();

function usePrompt(prompt) {
  promptInput.value = prompt;
  updateCommand();
  document.querySelector('.command-lab').scrollIntoView({ behavior: 'smooth', block: 'center' });
  window.setTimeout(() => promptInput.focus(), 450);
}

document.querySelectorAll('[data-use-prompt]').forEach((button) => {
  button.addEventListener('click', () => usePrompt(button.dataset.usePrompt));
});

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

document.querySelectorAll('[data-gallery-carousel]').forEach((carousel) => {
  const viewport = carousel.querySelector('[data-gallery-viewport]');
  const track = carousel.querySelector('[data-gallery-track]');
  const slides = [...carousel.querySelectorAll('[data-gallery-slide]')];
  const thumbs = [...carousel.querySelectorAll('[data-gallery-thumb]')];
  const statusTitle = carousel.querySelector('[data-gallery-status-title]');
  const count = carousel.querySelector('[data-gallery-count]');
  const kicker = carousel.querySelector('[data-gallery-kicker]');
  const title = carousel.querySelector('[data-gallery-title]');
  const description = carousel.querySelector('[data-gallery-description]');
  const prompt = carousel.querySelector('[data-gallery-prompt]');
  const useButton = carousel.querySelector('[data-gallery-use]');
  const copyButton = carousel.querySelector('[data-gallery-copy]');
  let currentIndex = 0;
  let pointerStart = null;

  function showSlide(index) {
    currentIndex = (index + slides.length) % slides.length;
    track.style.transform = `translateX(-${currentIndex * 100}%)`;
    slides.forEach((slide, slideIndex) => {
      const active = slideIndex === currentIndex;
      slide.classList.toggle('is-active', active);
      slide.setAttribute('aria-hidden', String(!active));
    });
    thumbs.forEach((thumb, thumbIndex) => {
      const active = thumbIndex === currentIndex;
      thumb.classList.toggle('is-active', active);
      thumb.setAttribute('aria-current', String(active));
    });
    const activeSlide = slides[currentIndex];
    statusTitle.textContent = activeSlide.dataset.title;
    count.textContent = `${String(currentIndex + 1).padStart(2, '0')} / ${String(slides.length).padStart(2, '0')}`;
    kicker.textContent = activeSlide.dataset.kicker;
    title.textContent = activeSlide.dataset.title;
    description.textContent = activeSlide.dataset.description;
    prompt.textContent = activeSlide.dataset.prompt;
    const activeThumb = thumbs[currentIndex];
    const thumbRail = activeThumb?.parentElement;
    if (activeThumb && thumbRail) {
      const targetLeft = activeThumb.offsetLeft - (thumbRail.clientWidth - activeThumb.clientWidth) / 2;
      thumbRail.scrollTo({ left: Math.max(0, targetLeft), behavior: reducedMotion ? 'auto' : 'smooth' });
    }
  }

  carousel.querySelector('[data-gallery-previous]')?.addEventListener('click', (event) => {
    event.stopPropagation();
    showSlide(currentIndex - 1);
  });
  carousel.querySelector('[data-gallery-next]')?.addEventListener('click', (event) => {
    event.stopPropagation();
    showSlide(currentIndex + 1);
  });
  thumbs.forEach((thumb, index) => thumb.addEventListener('click', (event) => {
    event.stopPropagation();
    showSlide(index);
  }));
  copyButton?.addEventListener('click', () => copyText(slides[currentIndex].dataset.prompt));
  useButton?.addEventListener('click', () => usePrompt(slides[currentIndex].dataset.prompt));
  viewport?.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowRight') showSlide(currentIndex + 1);
    if (event.key === 'ArrowLeft') showSlide(currentIndex - 1);
  });
  viewport?.addEventListener('pointerdown', (event) => {
    pointerStart = event.clientX;
  });
  viewport?.addEventListener('pointerup', (event) => {
    if (pointerStart === null) return;
    const distance = event.clientX - pointerStart;
    pointerStart = null;
    if (Math.abs(distance) < 46) return;
    showSlide(currentIndex + (distance < 0 ? 1 : -1));
  });
  viewport?.addEventListener('pointercancel', () => { pointerStart = null; });

  showSlide(0);
});

if ('IntersectionObserver' in window && !reducedMotion) {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });
  document.querySelectorAll('[data-reveal]').forEach((element) => observer.observe(element));
} else {
  document.querySelectorAll('[data-reveal]').forEach((element) => element.classList.add('is-visible'));
}
