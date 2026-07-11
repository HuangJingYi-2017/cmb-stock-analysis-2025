/**
 * TASK4: 海龟交易法 - 页面交互脚本
 */

document.addEventListener('DOMContentLoaded', function() {
  // 当前页面导航高亮
  const currentPage = window.location.pathname.split('/').pop();
  document.querySelectorAll('.main-nav a').forEach(link => {
    if (link.getAttribute('href').includes(currentPage)) {
      link.classList.add('active');
    }
  });

  // 图片点击放大预览
  document.querySelectorAll('.image-card img').forEach(img => {
    img.style.cursor = 'zoom-in';
    img.addEventListener('click', function() {
      window.open(this.src, '_blank');
    });
  });

  // 参数对比表数值着色
  document.querySelectorAll('.param-table .num').forEach(cell => {
    const text = cell.textContent.trim().replace(/[,%+]/g, '');
    const val = parseFloat(text);
    if (!isNaN(val)) {
      if (val > 0) cell.classList.add('positive');
      else if (val < 0) cell.classList.add('negative');
    }
  });

  // 指标表数值着色
  document.querySelectorAll('.metrics-table .num').forEach(cell => {
    const text = cell.textContent.trim().replace(/[,%+]/g, '');
    const val = parseFloat(text);
    if (!isNaN(val)) {
      if (val > 0) cell.classList.add('positive');
      else if (val < 0) cell.classList.add('negative');
    }
  });
});
