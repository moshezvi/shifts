/**
 * Hebrew role labels by stored codes + gender (M/F).
 * See docs/shifts-domain.md (Hebrew UI terminology).
 */
function roleLabelHe(role, gender) {
  var f = gender === "F";
  if (role === "support") return f ? "סייעת" : "סייע";
  if (role === "oncall") return f ? "כוננית" : "כונן";
  if (role === "admin") return f ? "מנהלת" : "מנהל";
  return role;
}
