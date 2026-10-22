"""Dev only: effects for checking the scripted pages in a game that is left open.

    python -I tools/check_effects.py            write common/scripted_effects/mod1440_check.txt; a running game
                                                reads it within seconds ("Reloading Database" in error.log)
    python -I tools/check_effects.py --restore  remove it again. The test suite fails while it is there.

Each effect is run from the console with nothing selected: effect mod1440_chk_<name>. They change the game of
the check, which is never saved. What an effect finds out goes to game.log as a line "MOD1440 ...".

They are for a new game as Germany on 1 January 1936, the clean state of tools/Invoke-GameSteps.ps1 -Start;
those named rt56 are for the map of Road to 56, as the United States.
The notes of each phase say which were used for what (wiki/phases/E1-war-diary.md, "Game checks").
"""
import io
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "common", "scripted_effects", "mod1440_check.txt")

EFFECTS = """# CHECK ONLY: written by tools/check_effects.py, removed with --restore.

# ---- events, caused while paused (as Germany on 1 January 1936)

# War on Poland, and on Czechoslovakia.
mod1440_chk_war = {
	declare_war_on = { target = POL type = annex_everything }
}

mod1440_chk_war2 = {
	declare_war_on = { target = CZE type = annex_everything }
}

mod1440_chk_peace = {
	white_peace = POL
}

# Czechoslovakia annexed (needs the war first for a line about it).
mod1440_chk_annex = {
	annex_country = { target = CZE transfer_troops = no }
}

# Denmark made a subject.
mod1440_chk_puppet = {
	puppet = DEN
}

# Niederschlesien lost to Poland and taken back; Danzig taken.
mod1440_chk_state = {
	POL = { set_state_controller = 66 }
	set_state_controller = 66
}

mod1440_chk_state2 = {
	set_state_controller = 85
}

# Brandenburg, the capital's state, lost to Poland and taken back.
mod1440_chk_capital = {
	POL = { set_state_controller = 64 }
	set_state_controller = 64
}

# The copy of who holds each victory point, taken now, with a line in game.log.
mod1440_chk_sync = {
	mod1440_vp_sync = yes
	log = "MOD1440 check: sync, [?mod1440_vp_ctl^num] points, version [?mod1440_vp_ver], first holder [?mod1440_vp_ctl^0.GetName], Berlin [?global.province_controllers^6521.GetName]"
}

# Thorn (5 points): the territory log only
mod1440_chk_vp1 = {
	set_province_controller = 3295
	mod1440_vp_scan = yes
}

# Krakau (20 points): both logs
mod1440_chk_vp2 = {
	set_province_controller = 9427
	mod1440_vp_scan = yes
}

# Breslau (10 points) lost to Poland
mod1440_chk_vp3 = {
	POL = { set_province_controller = 9570 }
	mod1440_vp_scan = yes
}

# A promotion and a skill level for the third general of the game's list, and a general made by effect.
mod1440_chk_officers = {
	set_temp_variable = { c_g = army_leaders^2 }
	var:c_g = {
		promote_leader = yes
		add_skill_level = 1
	}
	create_corps_commander = {
		name = "Check General"
		skill = 2
		attack_skill = 2
		defense_skill = 2
		planning_skill = 1
		logistics_skill = 1
	}
}

# A general made by create_corps_commander: he has a number, and no portrait of his own.
mod1440_chk_gen = {
	create_corps_commander = {
		name = "Check General"
		skill = 1
		attack_skill = 1
		defense_skill = 1
		planning_skill = 1
		logistics_skill = 1
	}
}

# Two characters without a command get one by effect, the way focuses and most mods add generals: such a
# leader has no number (Engine Facts X66). With a legacy id and without: it makes no difference.
mod1440_chk_by_effect = {
	set_temp_variable = { ref_a = 0 }
	set_temp_variable = { ref_b = 0 }
	every_character = {
		limit = { NOT = { is_corps_commander = yes } NOT = { is_field_marshal = yes } NOT = { is_navy_leader = yes } }
		random_select_amount = 1
		add_corps_commander_role = {
			legacy_id = 77001
			skill = 1
			attack_skill = 1
			defense_skill = 1
			planning_skill = 1
			logistics_skill = 1
		}
		set_temp_variable = { ref_a = THIS }
		save_global_event_target_as = mod1440_chk_a
	}
	every_character = {
		limit = { NOT = { is_corps_commander = yes } NOT = { is_field_marshal = yes } NOT = { is_navy_leader = yes } }
		random_select_amount = 1
		add_corps_commander_role = {
			skill = 1
			attack_skill = 1
			defense_skill = 1
			planning_skill = 1
			logistics_skill = 1
		}
		set_temp_variable = { ref_b = THIS }
		save_global_event_target_as = mod1440_chk_b
	}
	log = "MOD1440 legacy: with id [mod1440_chk_a.GetName] THIS [?ref_a] [?ref_a.GetName] | without [mod1440_chk_b.GetName] THIS [?ref_b] [?ref_b.GetName]"
}

# The fifth general of the game's list retires.
mod1440_chk_retire = {
	set_temp_variable = { c_g = army_leaders^4 }
	var:c_g = { retire = yes }
}

# Four German advisors hired.
mod1440_chk_hire = {
	activate_advisor = konstantin_von_neurath
	activate_advisor = todt
	activate_advisor = werner_von_fritsch_army_chief
	activate_advisor = gerd_von_rundstedt
}

# ---- the rounds the game runs by itself

# The daily round of the Records, now.
mod1440_chk_daily = {
	mod1440_rec_daily = yes
}

# The search for the places of leaders without a number, with what it found in game.log. Two lines with
# the same second mean it took less than one.
mod1440_chk_refs = {
	log = "MOD1440 refs: start"
	mod1440_of_refs = yes
	log = "MOD1440 refs: done, stale [?rf_stale] need [?rf_need] found [?rf_found] moved [?rf_old^num] top [?global.mod1440_ch_top] known [?mod1440_of_known^num] rows [?mod1440_of_rows^num]"
}

# The comparison of the victory points 400 times, between lines of game.log.
mod1440_chk_time = {
	log = "MOD1440 time: start"
	for_loop_effect = {
		start = 0
		end = 200
		value = chk_n
		mod1440_vp_scan = yes
	}
	log = "MOD1440 time: 200 scans done"
	for_loop_effect = {
		start = 0
		end = 200
		value = chk_n
		mod1440_vp_scan = yes
	}
	log = "MOD1440 time: 400 scans done"
}

# ---- a game as something else left it

# As a game saved with the build of 2026-10-12: the logs and the wars without their newer parts.
mod1440_chk_old = {
	clear_array = mod1440_ev_c
	clear_array = mod1440_ev_sc
	clear_array = mod1440_ev_p
	clear_array = mod1440_ev_x
	clear_array = mod1440_tr_c
	clear_array = mod1440_tr_sc
	clear_array = mod1440_tr_p
	clear_array = mod1440_tr_x
	clear_array = mod1440_wr_vpt
	clear_array = mod1440_wr_vpl
	clear_array = mod1440_wo_vpt
	clear_array = mod1440_wo_vpl
	mod1440_chk_sizes = yes
}

# As if the game's list of characters had changed: everybody the mod keeps by his place believes he stood three
# places further on, and so do the lists.
mod1440_chk_shift = {
	set_temp_variable = { sh = 0 }
	every_unit_leader = {
		limit = { check_variable = { mod1440_ch_at > 0 } }
		add_to_variable = { mod1440_ch_at = 0.00003 }
		add_to_temp_variable = { sh = 1 }
	}
	for_loop_effect = {
		start = 0
		end = mod1440_of_known^num
		value = sh_i
		if = { limit = { check_variable = { mod1440_of_known^sh_i > 5368 } } add_to_variable = { mod1440_of_known^sh_i = 0.00003 } }
	}
	for_loop_effect = {
		start = 0
		end = mod1440_ev_a^num
		value = sh_i
		if = { limit = { check_variable = { mod1440_ev_sa^sh_i = 1 } check_variable = { mod1440_ev_a^sh_i > 5368 } } add_to_variable = { mod1440_ev_a^sh_i = 0.00003 } }
	}
	if = { limit = { check_variable = { mod1440_of_sel > 5368 } } add_to_variable = { mod1440_of_sel = 0.00003 } }
	add_to_variable = { global.mod1440_ch_top = 0.00003 }
	log = "MOD1440 shift: [?sh] leaders moved, top [?global.mod1440_ch_top]"
}

# ---- with the map of Road to 56 (the playset of 2026-10-13), as the United States after the console's "tag USA"

# Which map the mod takes the loaded game for: its number of states, and the table (0 is the game's own).
mod1440_chk_map = {
	mod1440_vp_map = yes
	log = "MOD1440 check: [?vp_states] states, table [?vp_map], [?mod1440_vp_ctl^num] points copied, version [?mod1440_vp_ver]"
}

# War on Mexico.
mod1440_chk_rt56_war = {
	declare_war_on = { target = MEX type = annex_everything }
}

# Monterrey: 20 points in Tamaulipas on that map (the game's own: 10 points, and another state). Both logs.
mod1440_chk_rt56_vp1 = {
	set_province_controller = 12835
	mod1440_vp_scan = yes
}

# Tampico: a point only that map has.
mod1440_chk_rt56_vp2 = {
	set_province_controller = 5021
	mod1440_vp_scan = yes
}

# Eureka in California, a point only that map has, lost to Mexico.
mod1440_chk_rt56_vp3 = {
	MEX = { set_province_controller = 610 }
	mod1440_vp_scan = yes
}

# Whether a condition on an idea nobody defined is an error: read error.log after the reload, then run it.
mod1440_chk_idea = {
	if = {
		limit = { has_idea = mod1440_chk_no_such_idea }
		log = "MOD1440 check: an idea nobody defined is held"
	}
	else = {
		log = "MOD1440 check: an idea nobody defined is not held"
	}
}

# ---- the officers' traits and the file's new values (e-officers-gov, 2026-10-16)

# The cost of the trait round: every officer's traits made again ten times, between two lines of game.log
# (the daily round does it once, for an officer whose num_traits has changed). Then what each officer holds.
mod1440_chk_traits = {
	log = "MOD1440 traits: start"
	for_loop_effect = {
		start = 0
		end = 10
		value = chk_n
		every_army_leader = { mod1440_of_traits = yes }
		every_navy_leader = { mod1440_of_traits = yes }
	}
	log = "MOD1440 traits: 10 rounds done"
	every_army_leader = {
		log = "MOD1440 traits: [THIS.GetName] num_traits [?num_traits] named [?mod1440_of_tr_k] icons [?mod1440_of_tr_i] plus [?mod1440_of_tr_plus] first [?mod1440_of_tr^0.GetTokenKey] max [?num_max_traits] planning [?avg_unit_planning_ratio] battalions [?num_battalions] fighting [?num_units_in_combat] armoured [?num_armored]"
	}
	every_navy_leader = {
		log = "MOD1440 traits: [THIS.GetName] num_traits [?num_traits] named [?mod1440_of_tr_k] ships [?num_ships] carrier [?num_ships_with_type@carrier] capital [?num_ships_with_type@capital] screen [?num_ships_with_type@screen] submarine [?num_ships_with_type@submarine]"
	}
}

# Whether a condition on a trait the loaded game does not define is an error: read error.log after it.
mod1440_chk_trait_unknown = {
	every_army_leader = {
		limit = { is_field_marshal = yes }
		if = {
			limit = { has_trait = mod1440_chk_no_such_trait }
			log = "MOD1440 check: a trait nobody defined is held by [THIS.GetName]"
		}
		else = {
			log = "MOD1440 check: a trait nobody defined is not held by [THIS.GetName]"
		}
	}
}

# ---- numbers into game.log

# Who the game counts as an officer, each way script can ask (the generals another mod adds were missing).
mod1440_chk_leaders = {
	set_temp_variable = { n_arr = army_leaders^num }
	set_temp_variable = { n_nav = navy_leaders^num }
	set_temp_variable = { n_eal = 0 }
	every_army_leader = { add_to_temp_variable = { n_eal = 1 } }
	set_temp_variable = { n_eal_inv = 0 }
	every_army_leader = { include_invisible = yes add_to_temp_variable = { n_eal_inv = 1 } }
	set_temp_variable = { n_enl = 0 }
	every_navy_leader = { add_to_temp_variable = { n_enl = 1 } }
	set_temp_variable = { n_eul = 0 }
	every_unit_leader = { add_to_temp_variable = { n_eul = 1 } }
	set_temp_variable = { n_ech = 0 }
	every_character = { add_to_temp_variable = { n_ech = 1 } }
	set_temp_variable = { n_role = 0 }
	every_character = {
		limit = { OR = { is_corps_commander = yes is_field_marshal = yes is_navy_leader = yes } }
		add_to_temp_variable = { n_role = 1 }
	}
	log = "MOD1440 leaders [GetTag]: army_leaders [?n_arr] navy_leaders [?n_nav] every_army_leader [?n_eal] with invisible [?n_eal_inv] every_navy_leader [?n_enl] every_unit_leader [?n_eul] every_character [?n_ech] with a command [?n_role] known [?mod1440_of_known^num] rows [?mod1440_of_rows^num]"
}

# How long each part of the two logs and of the wars is.
mod1440_chk_sizes = {
	log = "MOD1440 check: sizes ev [?mod1440_ev_date^num]/[?mod1440_ev_c^num]/[?mod1440_ev_sc^num]/[?mod1440_ev_p^num]/[?mod1440_ev_x^num] tr [?mod1440_tr_date^num]/[?mod1440_tr_c^num]/[?mod1440_tr_sc^num]/[?mod1440_tr_p^num]/[?mod1440_tr_x^num] wr [?mod1440_wr_enemy^num]/[?mod1440_wr_vpt^num]/[?mod1440_wr_vpl^num] wo [?mod1440_wo_enemy^num]/[?mod1440_wo_vpt^num]/[?mod1440_wo_vpl^num]"
}

# The Records in numbers.
mod1440_chk_log = {
	log = "MOD1440 check: ev [?mod1440_ev_date^num] tr [?mod1440_tr_date^num] c [?mod1440_tr_c^num] x [?mod1440_tr_x^num] enemies [?mod1440_ev_enemies^num] wr [?mod1440_wr_enemy^num] vpt [?mod1440_wr_vpt^num] wo [?mod1440_wo_enemy^num] sel [?mod1440_wr_sel_kind]/[?mod1440_wr_sel_i] has [?mod1440_wr_c_has] lines [?mod1440_wr_ln_n] view [?mod1440_wd_fam^num] ctl [?mod1440_vp_ctl^num] ver [?mod1440_vp_ver]"
}

# ---- e-diary-wars (2026-10-16): logs of 1000 lines, marks, the per-war counters

# Both logs filled to their 1000 lines with made-up lines (Danzig taken from Poland, at war with Poland), between two
# lines of game.log: two lines with the same second mean the 2000 writes took less than one.
mod1440_chk_fill = {
	log = "MOD1440 fill: start, ev [?mod1440_ev_date^num] tr [?mod1440_tr_date^num]"
	POL = { set_temp_variable = { chk_pol = THIS } }
	for_loop_effect = {
		start = 0
		end = 1000
		value = chk_n
		set_temp_variable = { ev_kind = token:mod1440_ev_state_taken }
		set_temp_variable = { ev_fam = 2 }
		set_temp_variable = { ev_kid = 14 }
		set_temp_variable = { ev_sa = 2 }
		set_temp_variable = { ev_a = 85 }
		set_temp_variable = { ev_sb = 1 }
		set_temp_variable = { ev_b = chk_pol }
		set_temp_variable = { ev_so = 0 }
		set_temp_variable = { ev_o = 0 }
		set_temp_variable = { ev_p = 0 }
		set_temp_variable = { ev_x = 0 }
		mod1440_tr_add = yes
		set_temp_variable = { ev_kind = token:mod1440_ev_war_with }
		set_temp_variable = { ev_fam = 1 }
		set_temp_variable = { ev_kid = 3 }
		set_temp_variable = { ev_sa = 0 }
		set_temp_variable = { ev_a = 0 }
		mod1440_ev_add = yes
	}
	log = "MOD1440 fill: done, ev [?mod1440_ev_date^num] tr [?mod1440_tr_date^num] ids [?mod1440_ev_id^num]/[?mod1440_tr_id^num] next [?mod1440_ln_next]"
}

# The diary's All view (both logs together, 200 rows with day headers) made 20 times, between lines of game.log.
mod1440_chk_list_time = {
	set_variable = { mod1440_wd_filter = 0 }
	set_variable = { mod1440_wd_from = 0 }
	log = "MOD1440 list: start"
	for_loop_effect = {
		start = 0
		end = 20
		value = chk_n
		mod1440_wd_list = yes
	}
	log = "MOD1440 list: 20 views done, rows [?mod1440_wd_fam^num] lines [?mod1440_wd_shown] of [?mod1440_wd_total]"
}

# The file of the chosen war made 20 times (its lines, the marks of its track, the commanders' tally).
mod1440_chk_card_time = {
	log = "MOD1440 card: start"
	for_loop_effect = {
		start = 0
		end = 20
		value = chk_n
		mod1440_wr_card = yes
	}
	log = "MOD1440 card: 20 files done, lines [?mod1440_wr_ln_n] commanders [?mod1440_wr_k_n] id [?mod1440_wr_c_id] first mark x [?mod1440_wr_mx^0]"
}

# The newest line of the main log marked, as its box would: the chronicle and the mark in both logs.
mod1440_chk_mark = {
	set_temp_variable = { mk_src = 1 }
	set_temp_variable = { mk_si = mod1440_ev_date^num }
	subtract_from_temp_variable = { mk_si = 1 }
	mod1440_wd_mark = yes
	log = "MOD1440 mark: chronicle [?mod1440_kp_date^num], the line's mark [?mod1440_ev_k^mk_si], its number [?mod1440_ev_id^mk_si]"
}

# As a game saved with the build of 2026-10-13: the logs without marks and numbers, the wars without their numbers,
# the enemy's casualties and the outcome as a number, the honours with one switch.
mod1440_chk_old2 = {
	clear_array = mod1440_ev_k
	clear_array = mod1440_ev_id
	clear_array = mod1440_tr_k
	clear_array = mod1440_tr_id
	clear_array = mod1440_wr_id
	clear_array = mod1440_wr_ecas0
	clear_array = mod1440_wr_ecas
	clear_array = mod1440_wo_id
	clear_array = mod1440_wo_day0
	clear_array = mod1440_wo_ecas
	clear_array = mod1440_wo_oc
	clear_array = mod1440_wo_fr
	clear_variable = mod1440_hn_v
	clear_variable = mod1440_hn_sea
	clear_variable = mod1440_hn_air
	mod1440_chk_sizes2 = yes
}

# ---- the top bar strip (D7)

# As a save of a build before D7: the strip's variables gone, so the fixed twin of the eight defaults shows until
# the first click on the edit button or the next day.
mod1440_chk_tb_old = {
	clear_variable = mod1440_tb_ver
	clear_variable = mod1440_tb_setup
	log = "MOD1440 tb: as an earlier build, version [?mod1440_tb_ver]"
}

# Every value the strip can show, and its placement, in game.log: compare with the game's tooltips.
mod1440_chk_tb_log = {
	log = "MOD1440 tb: pp [?political_power_daily|2] cp [?command_power_daily|2] stab [?modifier@stability_weekly|3] ws [?modifier@war_support_weekly|3] civ [?num_of_civilian_factories] free [?num_of_civilian_factories_available_for_projects] mil [?num_of_military_factories] idle [?num_of_available_military_factories] dock [?num_of_naval_factories] idle [?num_of_available_naval_factories] cg [?modifier@consumer_goods_factor|3] fuel [?fuel_k|1]/[?max_fuel_k|1] field [?deployed_total_manpower_k|1] training [?amount_manpower_in_deployment_queue]"
	log = "MOD1440 tb: oil [?resource@oil] alu [?resource@aluminium] rubber [?resource@rubber] tungsten [?resource@tungsten] steel [?resource@steel] chromium [?resource@chromium] coal [?resource@coal]"
	log = "MOD1440 tb: version [?mod1440_tb_ver] used [?mod1440_tb_used] room [?mod1440_tb_room] pct [?mod1440_tb_used_pct|1] x pp [?mod1440_tb_x_pp] cp [?mod1440_tb_x_cp] stab [?mod1440_tb_x_stab] fuel [?mod1440_tb_x_fuel]"
}

# How long the newer parts are, and the honour switches.
mod1440_chk_sizes2 = {
	log = "MOD1440 check: sizes2 ev [?mod1440_ev_date^num]/[?mod1440_ev_k^num]/[?mod1440_ev_id^num] tr [?mod1440_tr_date^num]/[?mod1440_tr_k^num]/[?mod1440_tr_id^num] kp [?mod1440_kp_date^num] wr [?mod1440_wr_enemy^num]/[?mod1440_wr_id^num]/[?mod1440_wr_ecas0^num] wo [?mod1440_wo_enemy^num]/[?mod1440_wo_id^num]/[?mod1440_wo_oc^num]/[?mod1440_wo_fr^num] honours [?mod1440_hn_v] [?mod1440_hn_auto] [?mod1440_hn_sea] [?mod1440_hn_air] [?mod1440_hn_vp]"
}

# ---- Army Readiness, D2 round 2 fix round 1: why the first Location pass found no state. With a general given an
# army: the states every_controlled_state put into a temporary array, how many of them a loop in a general's
# scope sees, and his divisions summed over them both ways (SCR-021 says 30 for Germany's 30), then where the
# fixed pass (mod1440_ar_here) puts him.
mod1440_chk_ar_where = {
	clear_temp_array = c_where
	every_controlled_state = { add_to_temp_array = { c_where = THIS } }
	set_temp_variable = { c_n = c_where^num }
	log = "MOD1440 ar where: every_controlled_state put [?c_n] states into the temporary array"
	every_army_leader = {
		limit = { check_variable = { num_units > 0 } }
		set_temp_variable = { c_seen = 0 }
		set_temp_variable = { c_sum = 0 }
		for_each_loop = {
			array = c_where
			value = c_st
			add_to_temp_variable = { c_seen = 1 }
			add_to_temp_variable = { c_sum = num_units_in_state@var:c_st }
		}
		log = "MOD1440 ar where: [?THIS.GetName] has [?num_units] divisions; the loop in his scope saw [?c_seen] states and [?c_sum] of his divisions"
	}
	set_temp_variable = { c_sum2 = 0 }
	set_temp_variable = { c_me = THIS }
	for_each_scope_loop = {
		array = controlled_states
		set_temp_variable = { c_st = THIS }
		var:c_me = { every_army_leader = { limit = { check_variable = { num_units > 0 } } add_to_temp_variable = { c_sum2 = num_units_in_state@var:c_st } } }
	}
	log = "MOD1440 ar where: summed state by state from the country's own loop (the fixed form): [?c_sum2]"
	mod1440_ar_count = yes
	every_army_leader = {
		limit = { check_variable = { num_units > 0 } }
		log = "MOD1440 ar where: after the count [?THIS.GetName] stands in [?mod1440_al_loc.GetName] with [?mod1440_al_lcnt] divisions"
	}
}

# ---- Army Readiness, D2 round 2 fix round 3: a click on the row of a general without a number. Each element of
# the list (a place is above 5368, a number below 0) is entered as the row's change_scope enters it, and what the
# click and the row's buttons ask is logged: THIS, mod1440_of_me, his place, the rank conditions of the five twins
# of the row's button. Then the click's own effect runs for the first general kept by place (or the first row),
# and what the page reads after it is logged.
mod1440_chk_ar_pick = {
	log = "MOD1440 ar pick: [?mod1440_ar_leaders^num] rows; before: has_sel [?mod1440_ar_has_sel] sel [?mod1440_ar_sel] names [?mod1440_ar_names]"
	set_temp_variable = { c_pick = 0 }
	for_each_loop = {
		array = mod1440_ar_leaders
		value = c_l
		var:c_l = {
			set_temp_variable = { c_this = THIS }
			mod1440_of_me = yes
			set_temp_variable = { c_fm = 0 }
			if = { limit = { is_field_marshal = yes } set_temp_variable = { c_fm = 1 } }
			set_temp_variable = { c_nfm = 0 }
			if = { limit = { NOT = { is_field_marshal = yes } } set_temp_variable = { c_nfm = 1 } }
			set_temp_variable = { c_ag = 0 }
			if = { limit = { is_leading_army_group = yes } set_temp_variable = { c_ag = 1 } }
			set_temp_variable = { c_nag = 0 }
			if = { limit = { NOT = { is_leading_army_group = yes } } set_temp_variable = { c_nag = 1 } }
			log = "MOD1440 ar pick: element [?c_l] [?THIS.GetName]: THIS [?c_this] of_me [?of_me] ch_at [?mod1440_ch_at] pick [?mod1440_al_pick]; is_field_marshal [?c_fm] not [?c_nfm]; is_leading_army_group [?c_ag] not [?c_nag]"
		}
		if = { limit = { check_variable = { c_pick = 0 } check_variable = { c_l > 5368 } } set_temp_variable = { c_pick = c_l } }
	}
	if = { limit = { check_variable = { c_pick = 0 } check_variable = { mod1440_ar_leaders^num > 0 } } set_temp_variable = { c_pick = mod1440_ar_leaders^0 } }
	if = {
		limit = { NOT = { check_variable = { c_pick = 0 } } }
		var:c_pick = {
			mod1440_of_me = yes
			log = "MOD1440 ar pick: the click on [?THIS.GetName]: of_me [?of_me]"
			ROOT = { mod1440_ar_choose = yes }
		}
		log = "MOD1440 ar pick: after: has_sel [?mod1440_ar_has_sel] sel [?mod1440_ar_sel] ([?mod1440_ar_sel.GetName]), [?mod1440_ar_fill^num] kinds listed"
		for_each_loop = {
			array = mod1440_ar_leaders
			value = c_l
			var:c_l = { log = "MOD1440 ar pick: after: [?THIS.GetName] pick [?mod1440_al_pick]" }
		}
	}
}

# ---- Army Readiness, D2 round 2 fix round 2: what the armies list's rows see. Each element of the list's array is
# entered as the row's change_scope enters it, and every condition the row asks of Location and the HQ is logged
# with the raw values: which of them is true for a general whose state game.log names.
mod1440_chk_ar_row = {
	log = "MOD1440 ar row: [?mod1440_ar_leaders^num] rows"
	for_each_loop = {
		array = mod1440_ar_leaders
		value = c_l
		var:c_l = {
			set_temp_variable = { c_a = 0 }
			if = { limit = { check_variable = { mod1440_al_loc > 0 } } set_temp_variable = { c_a = 1 } }
			set_temp_variable = { c_z = 0 }
			if = { limit = { NOT = { check_variable = { mod1440_al_loc = 0 } } } set_temp_variable = { c_z = 1 } }
			set_temp_variable = { c_b = 0 }
			if = { limit = { check_variable = { mod1440_al_lcnt > 0 } } set_temp_variable = { c_b = 1 } }
			set_temp_variable = { c_c = 0 }
			if = { limit = { check_variable = { mod1440_al_hq > 0 } } set_temp_variable = { c_c = 1 } }
			set_temp_variable = { c_d = 0 }
			if = { limit = { NOT = { check_variable = { mod1440_al_hq = 0 } } } set_temp_variable = { c_d = 1 } }
			log = "MOD1440 ar row: [?c_l] [?THIS.GetName]: loc [?mod1440_al_loc] [?mod1440_al_loc.GetName], loc>0 [?c_a], loc not 0 [?c_z]; lcnt [?mod1440_al_lcnt], lcnt>0 [?c_b]; hq [?mod1440_al_hq] [?mod1440_al_hq.GetName], hq>0 [?c_c], hq not 0 [?c_d]; state_deployed [?state_deployed]; fill [?mod1440_al_fill]"
		}
	}
}
"""


H_SERIES = 31          # D4 round 2: the figures National Figures writes down (tools/build_managers.py, SERIES)
H_RES = range(20, 27)  # their resource balances, which go below zero


def history_months(name, months, years, filled=H_SERIES):
    """An effect that fills the arrays of the History page with made-up months, without running time: a rising
    figure, a falling one and a wave, by turns; the resource balances (D4 round 2) a wave around zero. years: with
    the year of each month, or without as a game saved before 2026-10-12 has them. filled: how many of the figures
    get months; 12 leaves the eight of 2026-10-16 and the eleven of 2026-10-17 empty, as a game saved by the build
    before 2026-10-16 has them, 20 the eleven, as a save of 2026-10-16 (the drawing pads them)."""
    series = "".join(("\t\tadd_to_array = { mod1440_h_%d = below }\n" if n in H_RES else
                      "\t\tadd_to_array = { mod1440_h_%d = up }\n" if n % 3 == 0 else
                      "\t\tadd_to_array = { mod1440_h_%d = down }\n" if n % 3 == 1 else
                      "\t\tadd_to_array = { mod1440_h_%d = wave }\n") % n for n in range(filled))
    forget = "".join("\t\t\tremove_from_array = { array = mod1440_h_%d index = 0 }\n" % n for n in range(filled))
    clear = "".join("\tclear_array = mod1440_h_%d\n" % n for n in range(H_SERIES))
    year = """		set_temp_variable = { mo = t }
		modulo_temp_variable = { mo = 12 }
		set_temp_variable = { yr = t }
		subtract_from_temp_variable = { yr = mo }
		divide_temp_variable = { yr = 12 }
		add_to_temp_variable = { yr = 1936 }
		add_to_array = { mod1440_h_year = yr }
""" if years else ""
    forget_year = "\t\t\tremove_from_array = { array = mod1440_h_year index = 0 }\n" if years else ""
    return """
%s = {
%s	clear_array = mod1440_h_date
	clear_array = mod1440_h_year
	for_loop_effect = {
		start = 0
		end = %d
		value = t
		set_temp_variable = { up = t }
		multiply_temp_variable = { up = t }
		add_to_temp_variable = { up = 9000 }
		set_temp_variable = { down = 130 }
		subtract_from_temp_variable = { down = t }
		set_temp_variable = { wave = t }
		modulo_temp_variable = { wave = 24 }
		add_to_temp_variable = { wave = 10 }
		set_temp_variable = { below = wave }
		subtract_from_temp_variable = { below = 22 }
%s		add_to_array = { mod1440_h_date = global.date }
%s		if = {
			limit = { check_variable = { mod1440_h_date^num > 120 } }
%s			remove_from_array = { array = mod1440_h_date index = 0 }
%s		}
	}
	mod1440_h_draw = yes
	log = "MOD1440 check: history filled, [?mod1440_h_date^num] months, [?mod1440_h_0^num] values, [?mod1440_h_year^num] years"
}
""" % (name, clear, months, series, year, forget, forget_year)


# 130 months with years (the oldest ten are forgotten), the same as an older save has them, seven months, and
# 130 months of the twelve figures a save of the build before 2026-10-16 has
HISTORY = ("\n# ---- the History page: made-up months\n"
           + history_months("mod1440_chk_months", 130, True) + history_months("mod1440_chk_months_old", 130, False)
           + history_months("mod1440_chk_months_few", 7, True) + history_months("mod1440_chk_months_twelve", 130, True, 12)
           + history_months("mod1440_chk_months_twenty", 130, True, 20))


def changed_month():
    """D4 round 2: the Changed view of National Figures. Writes the modifiers down as mod1440_h_record does on the
    first of the month, then makes four of them look different on that day (political power per day, political
    power gain, consumer goods share, research speed), so that the lists show those four as changed."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import build_managers
    names = build_managers.NF_MODIFIERS
    was = "".join("\tadd_to_array = { mod1440_nf_was = %s }\n" % value for value in names)
    changes = ""
    for value, delta in (("political_power_daily", "-0.25"), ("modifier@political_power_factor", "-0.05"),
                         ("modifier@consumer_goods_expected_value", "0.05"), ("modifier@research_speed_factor", "-0.05")):
        at = names.index(value)
        changes += "\tset_temp_variable = { c_w = mod1440_nf_was^%d }\n\tadd_to_temp_variable = { c_w = %s }\n" % (at, delta)
        changes += "\tset_variable = { mod1440_nf_was^%d = c_w }\n" % at
    return ("\n# ---- National Figures, D4 round 2: a made-up first of the month for the Changed view\n"
            "mod1440_chk_changed = {\n\tclear_array = mod1440_nf_was\n" + was + changes
            + "\tset_variable = { mod1440_nf_was_date = global.date }\n\tmod1440_nf_fill = yes\n"
            "\tlog = \"MOD1440 check: changed, [?mod1440_nf_was^num] modifiers, [?mod1440_nf_a0] [?mod1440_nf_a1] [?mod1440_nf_a2] [?mod1440_nf_a3] changed\"\n}\n")


HISTORY += changed_month()

if __name__ == "__main__":
    if "--restore" in sys.argv:
        if os.path.isfile(PATH):
            os.remove(PATH)
            print("removed", PATH)
    else:
        io.open(PATH, "w", encoding="utf-8", newline="\n").write(EFFECTS + HISTORY)
        print("wrote", PATH)
        # a running game reads the script again when a file under common/scripted_guis has a new time stamp
        folder = os.path.join(ROOT, "common", "scripted_guis")
        now = time.time()
        for name in os.listdir(folder):
            os.utime(os.path.join(folder, name), (now, now))
