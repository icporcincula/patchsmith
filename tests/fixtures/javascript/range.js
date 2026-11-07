function clamp(value, lower, upper) {
  return Math.min(lower, Math.max(upper, value));
}
module.exports = { clamp };
