function isVisuallyHidden(node) {
  if (!(node instanceof Element)) return true;

  const invisibleTags = ['script', 'style', 'meta', 'link', 'template', 'noscript'];
  const tagName = node.nodeName.toLowerCase();
  if (invisibleTags.includes(tagName)) return true;

  const style = getComputedStyle(node);
  const hiddenByStyle = (
    style.display === 'none' ||
    style.visibility === 'hidden'
    // 如果你想强制排除透明元素，再加上这一行：
    // || style.opacity === '0'
  );

  const hasNoSize = node.offsetWidth === 0 && node.offsetHeight === 0;

  return hiddenByStyle || hasNoSize;
}

function isMeaninglessNode(node) {
  if (!(node instanceof Element)) return true;

  const tagName = node.nodeName.toLowerCase();
  const isStructural = ['div', 'span', 'section', 'article', 'header', 'footer', 'main'].includes(tagName);

  const hasUsefulAttrs = node.id || node.getAttribute('class') || node.getAttribute('role');
  const hasUsefulText = node.textContent?.trim().length > 0;
  const hasChildren = node.children.length > 0;

  return isStructural && !hasUsefulAttrs && !hasUsefulText && !hasChildren;
}

function domTreeToJson(node = document.body, tagCounters = {}) {
  const getNodeLabel = (node) => {
    let name = node.nodeName.toLowerCase();
    if (node.id) name += `#${node.id}`;
    const classAttr = node.getAttribute('class');
    if (classAttr) {
      const classList = classAttr.trim().split(/\s+/).join('.');
      name += `.${classList}`;
    }
    const text = node.textContent?.trim().replace(/\s+/g, ' ') || '';
    const content = text ? ` content='${text.slice(0, 100)}${text.length > 100 ? "…" : ""}'` : '';
    return `${name}/` + content;
  };

  if (isVisuallyHidden(node) || isMeaninglessNode(node)) {
    return null;
  }

  const tagName = node.nodeName.toLowerCase();
  tagCounters[tagName] = (tagCounters[tagName] || 0);
  const nodeKey = `${tagName}${tagCounters[tagName]++}`;

  const children = Array.from(node.children)
    .map(child => domTreeToJson(child, tagCounters))
    .filter(childJson => childJson !== null);

  if (children.length === 0) {
    return { [nodeKey]: getNodeLabel(node) };
  } else {
    const childJson = {};
    children.forEach(child => Object.assign(childJson, child));
    return { [nodeKey]: childJson };
  }
}

function buildDomJsonTree(root = document.body) {
  const topTag = root.nodeName.toLowerCase();
  const result = {};
  result[topTag] = domTreeToJson(root);
  return result;
}

// 用法示例：
const domJson = buildDomJsonTree();
return JSON.stringify(domJson);