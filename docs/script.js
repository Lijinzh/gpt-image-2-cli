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

document.querySelectorAll('[data-use-prompt]').forEach((button) => {
  button.addEventListener('click', () => {
    promptInput.value = button.dataset.usePrompt;
    updateCommand();
    document.querySelector('.command-lab').scrollIntoView({ behavior: 'smooth', block: 'center' });
    window.setTimeout(() => promptInput.focus(), 450);
  });
});

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
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
