// #region agent log - Script loaded
console.log('=== PROJECT BUILDING INFO JS LOADED ===', new Date().toISOString());
console.log('=== PROJECT BUILDING INFO JS LOADED ===', new Date().toISOString());
console.log('=== PROJECT BUILDING INFO JS LOADED ===', new Date().toISOString());
// Alert to confirm script loads - remove after testing
if (typeof window !== 'undefined') {
	setTimeout(function() {
		console.log('PROJECT BUILDING INFO: Script executed, checking if form is available');
	}, 1000);
}
// #endregion

// Building Information Calculations
// Works for both Project Proposal and ERPNext Project DocTypes
console.log('[DEBUG BUILDING INFO] Registering Project Proposal event handlers');
frappe.ui.form.on('Project Proposal', {
	refresh: function(frm) {
		calculate_building_totals(frm);
		calculate_spaces_count(frm);
		// Recalculate all percentages on refresh
		if (frm.doc.total_land_area && frm.doc.total_land_area > 0) {
			calculate_area_percentages(frm);
		}
	},
	
	building_areas: function(frm, cdt, cdn) {
		calculate_building_totals(frm);
		calculate_area_percentages(frm, cdt, cdn);
	},
	
	include_in_total: function(frm, cdt, cdn) {
		// Recalculate totals when include_in_total checkbox changes
		calculate_building_totals(frm);
		calculate_area_percentages(frm, cdt, cdn);
	},
	
	building_spaces: function(frm, cdt, cdn) {
		calculate_spaces_count(frm);
	},
	
	total_land_area: function(frm) {
		calculate_area_percentages(frm);
		calculate_building_totals(frm);
		calculate_spaces_count(frm);
	}
});

frappe.ui.form.on('Project', {
	refresh: function(frm) {
		calculate_building_totals_custom(frm);
		calculate_spaces_count_custom(frm);
		// Recalculate all percentages on refresh
		if (frm.doc.total_land_area_custom && frm.doc.total_land_area_custom > 0) {
			calculate_area_percentages_custom(frm);
		}
	},
	
	building_areas_custom: function(frm, cdt, cdn) {
		console.log('[DEBUG BUILDING INFO] building_areas_custom table event fired', {cdt, cdn});
        
		calculate_building_totals_custom(frm);
		calculate_area_percentages_custom(frm, cdt, cdn);
	},
	
	include_in_total_custom: function(frm, cdt, cdn) {
		// Recalculate totals when include_in_total checkbox changes
		calculate_building_totals_custom(frm);
		calculate_area_percentages_custom(frm, cdt, cdn);
	},
	
	building_spaces_custom: function(frm, cdt, cdn) {
		// #region agent log - Parent form event fired
		console.log('[DEBUG BUILDING INFO] building_spaces_custom event fired', {frm_doctype: frm?.doctype, cdt, cdn});
		// #endregion
		calculate_spaces_count_custom(frm);
	},
	
	total_land_area_custom: function(frm) {
		calculate_area_percentages_custom(frm);
		calculate_building_totals_custom(frm);
		calculate_spaces_count_custom(frm);
	}
});

// Project Proposal Calculations
function calculate_building_totals(frm) {
	if (!frm.doc.building_areas || frm.doc.building_areas.length === 0) {
		frm.set_value('total_building_area', 0);
		frm.set_value('total_units', 0);
		frm.set_value('total_building_area_percentage', 0);
		return;
	}
	
	let total_area = 0;
	let total_units = 0;
	
	frm.doc.building_areas.forEach(function(row) {
		// Only include rows where include_in_total is checked (default is 1)
		const include_in_total = row.include_in_total !== undefined ? row.include_in_total : 1;
		
		if (include_in_total) {
			if (row.area_sqm) {
				total_area += parseFloat(row.area_sqm) || 0;
			}
			if (row.number_of_units) {
				total_units += parseInt(row.number_of_units) || 0;
			}
		}
	});
	
	frm.set_value('total_building_area', total_area);
	frm.set_value('total_units', total_units);
	
	// Calculate total building area percentage against total land area
	const total_land = parseFloat(frm.doc.total_land_area) || 0;
	const building_percentage = total_land > 0 ? (total_area / total_land) * 100 : 0;
	frm.set_value('total_building_area_percentage', Math.round(building_percentage * 1000) / 1000);
}

function calculate_area_percentages(frm, cdt, cdn) {
	// Use total_land_area as denominator for percentage calculation
	// Formula: percentage = (area_sqm / total_land_area) * 100
	const total_land_area = parseFloat(frm.doc.total_land_area) || 0;
	
	console.log('[DEBUG BUILDING INFO] calculate_area_percentages', {
		total_land_area: total_land_area,
		rows_count: frm.doc.building_areas ? frm.doc.building_areas.length : 0
	});
	
	// Always recalculate all rows to ensure consistency
	if (frm.doc.building_areas && total_land_area > 0) {
		frm.doc.building_areas.forEach(function(row) {
			if (row.name) {
				const area = parseFloat(row.area_sqm) || 0;
				const percentage = (area / total_land_area) * 100;
				// Round to 3 decimal places to avoid floating point issues
				const rounded_percentage = Math.round(percentage * 1000) / 1000;
				console.log('[DEBUG BUILDING INFO] Setting percentage', {
					row_name: row.name,
					area: area,
					total_land_area: total_land_area,
					percentage: rounded_percentage
				});
				frappe.model.set_value('Project Building Area Component', row.name, 'percentage', rounded_percentage);
			}
		});
	} else if (frm.doc.building_areas) {
		// If no total_land_area, set all percentages to 0
		frm.doc.building_areas.forEach(function(row) {
			if (row.name) {
				frappe.model.set_value('Project Building Area Component', row.name, 'percentage', 0);
			}
		});
	}
}

function calculate_spaces_count(frm) {
	if (!frm.doc.building_spaces || frm.doc.building_spaces.length === 0) {
		frm.set_value('total_spaces_count', 0);
		frm.set_value('total_spaces_area', 0);
		frm.set_value('total_spaces_percentage', 0);
		return;
	}
	
	let total_spaces_area = 0;
	
	frm.doc.building_spaces.forEach(function(row) {
		if (row.space_area) {
			total_spaces_area += parseFloat(row.space_area) || 0;
		}
	});
	
	frm.set_value('total_spaces_count', frm.doc.building_spaces.length);
	frm.set_value('total_spaces_area', total_spaces_area);
	
	// Calculate total spaces area percentage against total land area
	const total_land = parseFloat(frm.doc.total_land_area) || 0;
	const spaces_percentage = total_land > 0 ? (total_spaces_area / total_land) * 100 : 0;
	frm.set_value('total_spaces_percentage', Math.round(spaces_percentage * 1000) / 1000);
}

// ERPNext Project Custom Fields Calculations
function calculate_building_totals_custom(frm) {
	if (!frm.doc.building_areas_custom || frm.doc.building_areas_custom.length === 0) {
		frm.set_value('total_building_area_custom', 0);
		frm.set_value('total_units_custom', 0);
		frm.set_value('total_building_area_percentage_custom', 0);
		return;
	}
	
	let total_area = 0;
	let total_units = 0;
	
	frm.doc.building_areas_custom.forEach(function(row) {
		// Only include rows where include_in_total is checked (default is 1)
		const include_in_total = row.include_in_total !== undefined ? row.include_in_total : 1;
		
		if (include_in_total) {
			if (row.area_sqm) {
				total_area += parseFloat(row.area_sqm) || 0;
			}
			if (row.number_of_units) {
				total_units += parseInt(row.number_of_units) || 0;
			}
		}
	});
	
	frm.set_value('total_building_area_custom', total_area);
	frm.set_value('total_units_custom', total_units);
	
	// Calculate total building area percentage against total land area
	const total_land = parseFloat(frm.doc.total_land_area_custom) || 0;
	const building_percentage = total_land > 0 ? (total_area / total_land) * 100 : 0;
	frm.set_value('total_building_area_percentage_custom', Math.round(building_percentage * 1000) / 1000);
}

function calculate_area_percentages_custom(frm, cdt, cdn) {
	console.log('[DEBUG BUILDING INFO] calculate_area_percentages_custom called', {cdt, cdn});
	
	// Use total_land_area_custom as denominator for percentage calculation
	// Formula: percentage = (area_sqm / total_land_area_custom) * 100
	const total_land_area = parseFloat(frm.doc.total_land_area_custom) || 0;
	
	console.log('[DEBUG BUILDING INFO] calculate_area_percentages_custom', {
		total_land_area_custom: total_land_area,
		rows_count: frm.doc.building_areas_custom ? frm.doc.building_areas_custom.length : 0
	});
	
	// Always recalculate all rows to ensure consistency
	if (frm.doc.building_areas_custom && total_land_area > 0) {
		frm.doc.building_areas_custom.forEach(function(row) {
			if (row.name) {
				const area = parseFloat(row.area_sqm) || 0;
				const percentage = (area / total_land_area) * 100;
				// Round to 3 decimal places to avoid floating point issues
				const rounded_percentage = Math.round(percentage * 1000) / 1000;
				console.log('[DEBUG BUILDING INFO] Setting percentage for row', {
					row_name: row.name,
					area: area,
					total_land_area_custom: total_land_area,
					percentage: rounded_percentage
				});
				frappe.model.set_value('Project Building Area Component', row.name, 'percentage', rounded_percentage);
			}
		});
	} else if (frm.doc.building_areas_custom) {
		// If no total_land_area_custom, set all percentages to 0
		frm.doc.building_areas_custom.forEach(function(row) {
			if (row.name) {
				frappe.model.set_value('Project Building Area Component', row.name, 'percentage', 0);
			}
		});
	}
}

function calculate_spaces_count_custom(frm) {
	if (!frm.doc.building_spaces_custom || frm.doc.building_spaces_custom.length === 0) {
		frm.set_value('total_spaces_count_custom', 0);
		frm.set_value('total_spaces_area_custom', 0);
		frm.set_value('total_spaces_percentage_custom', 0);
		return;
	}
	
	let total_spaces_area = 0;
	
	frm.doc.building_spaces_custom.forEach(function(row) {
		if (row.space_area) {
			total_spaces_area += parseFloat(row.space_area) || 0;
		}
	});
	
	frm.set_value('total_spaces_count_custom', frm.doc.building_spaces_custom.length);
	frm.set_value('total_spaces_area_custom', total_spaces_area);
	
	// Calculate total spaces area percentage against total land area
	const total_land = parseFloat(frm.doc.total_land_area_custom) || 0;
	const spaces_percentage = total_land > 0 ? (total_spaces_area / total_land) * 100 : 0;
	frm.set_value('total_spaces_percentage_custom', Math.round(spaces_percentage * 1000) / 1000);
}

// Child table row calculations - works for both Project Proposal and ERPNext Project
frappe.ui.form.on('Project Building Area Component', {
	area_sqm: function(frm, cdt, cdn) {
		console.log('[DEBUG BUILDING INFO] area_sqm event fired', {frm_doctype: frm?.doctype, cdt, cdn, has_frm: !!frm});
		
		if (!frm) {
			console.log('[DEBUG BUILDING INFO] No frm available, trying cur_frm');
			frm = cur_frm;
		}
		
		if (!frm) {
			console.log('[DEBUG BUILDING INFO] No frm available, cannot calculate');
			return;
		}
		
		if (frm.doctype === 'Project Proposal') {
			console.log('[DEBUG BUILDING INFO] Calculating for Project Proposal');
			calculate_building_totals(frm);
			calculate_area_percentages(frm, cdt, cdn);
		} else if (frm.doctype === 'Project') {
			console.log('[DEBUG BUILDING INFO] Calculating for Project');
			calculate_building_totals_custom(frm);
			calculate_area_percentages_custom(frm, cdt, cdn);
		} else {
			console.log('[DEBUG BUILDING INFO] Unknown doctype:', frm.doctype);
		}
	},
	number_of_units: function(frm, cdt, cdn) {
		if (!frm) frm = cur_frm;
		if (!frm) return;
		
		if (frm.doctype === 'Project Proposal') {
			calculate_building_totals(frm);
		} else if (frm.doctype === 'Project') {
			calculate_building_totals_custom(frm);
		}
	},
	include_in_total: function(frm, cdt, cdn) {
		// Recalculate when checkbox changes
		if (!frm) frm = cur_frm;
		if (!frm) return;
		
		console.log('[DEBUG BUILDING INFO] include_in_total checkbox changed', {frm_doctype: frm?.doctype, cdt, cdn});
		
		if (frm.doctype === 'Project Proposal') {
			calculate_building_totals(frm);
			calculate_area_percentages(frm, cdt, cdn);
		} else if (frm.doctype === 'Project') {
			calculate_building_totals_custom(frm);
			calculate_area_percentages_custom(frm, cdt, cdn);
		}
	}
});

// #region agent log - Event handler registration
console.log('[DEBUG BUILDING INFO] Registering Project Building Space event handlers');
// #endregion

// Child table row calculations for Project Building Space
// Following Frappe patterns from opportunity.js and expense_claim.js
frappe.ui.form.on('Project Building Space', {
	length: function(frm, cdt, cdn) {
		// #region agent log - Event fired
		console.log('[DEBUG BUILDING INFO] length event fired', {frm_doctype: frm?.doctype, cdt, cdn, has_frm: !!frm});
		// #endregion
		
		// Get the child row directly from locals
		var child = locals[cdt][cdn];
		
		// #region agent log - Check locals
		console.log('[DEBUG BUILDING INFO] locals check', {has_child: !!child, child_length: child?.length, child_width: child?.width});
		// #endregion
		
		if (!child) {
			console.log('[DEBUG BUILDING INFO] No child row found, returning');
			return;
		}
		
		// Get current values
		const length = parseFloat(child.length) || 0;
		const width = parseFloat(child.width) || 0;
		
		// #region agent log - Before calculation
		console.log('[DEBUG BUILDING INFO] before calculation', {length, width, calculated_area: length * width});
		// #endregion
		
		// Calculate area
		if (length > 0 && width > 0) {
			const area = length * width;
			console.log('[DEBUG BUILDING INFO] Setting space_area to', area);
			frappe.model.set_value(cdt, cdn, 'space_area', area);
			console.log('[DEBUG BUILDING INFO] space_area set successfully');
		} else {
			console.log('[DEBUG BUILDING INFO] Setting space_area to 0 (length or width is 0)');
			frappe.model.set_value(cdt, cdn, 'space_area', 0);
		}
		
		// Update spaces count
		if (frm.doctype === 'Project Proposal') {
			calculate_spaces_count(frm);
		} else if (frm.doctype === 'Project') {
			calculate_spaces_count_custom(frm);
		}
	},
	width: function(frm, cdt, cdn) {
		// #region agent log - Event fired
		console.log('[DEBUG BUILDING INFO] width event fired', {frm_doctype: frm?.doctype, cdt, cdn, has_frm: !!frm});
		// #endregion
		
		// Get the child row directly from locals
		var child = locals[cdt][cdn];
		
		// #region agent log - Check locals
		console.log('[DEBUG BUILDING INFO] locals check', {has_child: !!child, child_length: child?.length, child_width: child?.width});
		// #endregion
		
		if (!child) {
			console.log('[DEBUG BUILDING INFO] No child row found, returning');
			return;
		}
		
		// Get current values
		const length = parseFloat(child.length) || 0;
		const width = parseFloat(child.width) || 0;
		
		// #region agent log - Before calculation
		console.log('[DEBUG BUILDING INFO] before calculation', {length, width, calculated_area: length * width});
		// #endregion
		
		// Calculate area
		if (length > 0 && width > 0) {
			const area = length * width;
			console.log('[DEBUG BUILDING INFO] Setting space_area to', area);
			frappe.model.set_value(cdt, cdn, 'space_area', area);
			console.log('[DEBUG BUILDING INFO] space_area set successfully');
		} else {
			console.log('[DEBUG BUILDING INFO] Setting space_area to 0 (length or width is 0)');
			frappe.model.set_value(cdt, cdn, 'space_area', 0);
		}
		
		// Update spaces count
		if (frm.doctype === 'Project Proposal') {
			calculate_spaces_count(frm);
		} else if (frm.doctype === 'Project') {
			calculate_spaces_count_custom(frm);
		}
	},
	space_area: function(frm, cdt, cdn) {
		if (frm.doctype === 'Project Proposal') {
			calculate_spaces_count(frm);
		} else if (frm.doctype === 'Project') {
			calculate_spaces_count_custom(frm);
		}
	}
});

// #region agent log - Event handler registration complete
console.log('[DEBUG BUILDING INFO] Project Building Space handlers registered');
// #endregion
