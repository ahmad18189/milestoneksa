// frappe.ready(() => {
//   // Only run this on List View pages
//   if (!frappe.listview_settings || frappe.get_route()[0] !== "List") return;

//   // Wait until the Gantt is drawn
//   const interval = setInterval(() => {
//     const svg = document.querySelector("svg.gantt");
//     if (svg) {
//       const container = svg.parentElement;
//       if (container) {
//         container.style.overflowX = "auto";
//         container.style.maxWidth = "100%";
//         container.style.border = "2px dashed red";  // debug aid

//         const bar = svg.querySelector("rect.bar");
//         if (bar) {
//           bar.scrollIntoView({ behavior: "smooth", inline: "start" });
//         }

//         console.log("✅ Gantt patch applied");
//         clearInterval(interval);
//       }
//     }
//   }, 500);
// });
