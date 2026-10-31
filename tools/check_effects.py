"""Dev only: effects for checking the scripted pages in a game that is left open.

    python -I tools/check_effects.py            write common/scripted_effects/mod1440_check.txt; a running game
                                                reads it within seconds ("Reloading Database" in error.log)
    python -I tools/check_effects.py --probe    the same, and the throwaway portrait probe of phase E7 (its window,
                                                script, texts and scene tools/scenes/probe_portraits.json)
    python -I tools/check_effects.py --restore  remove all of it again. The test suite fails while any is there:
    python -I tools/check_effects.py --check    exits 1 while a file of this tool is present.

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
	# E7 fix round 1: with Road to 56 (1.19.4) only Rundstedt was hired (check 2): the roles of Neurath, Todt and Fritsch
	# are gated by focuses and flags (available, visible). Who is still not hired gets a role of the check's own, hired at
	# once (add_advisor_role, activate = yes), in the same slot.
	if = {
		limit = { has_character = GER_konstantin_von_neurath NOT = { any_character = { is_character = GER_konstantin_von_neurath is_hired_as_advisor = yes } } }
		add_advisor_role = { character = GER_konstantin_von_neurath advisor = { slot = political_advisor idea_token = mod1440_chk_neurath cost = 0 } activate = yes }
	}
	if = {
		limit = { has_character = GER_fritz_todt NOT = { any_character = { is_character = GER_fritz_todt is_hired_as_advisor = yes } } }
		add_advisor_role = { character = GER_fritz_todt advisor = { slot = political_advisor idea_token = mod1440_chk_todt cost = 0 } activate = yes }
	}
	if = {
		limit = { has_character = GER_werner_von_fritsch NOT = { any_character = { is_character = GER_werner_von_fritsch is_army_chief = yes } } }
		add_advisor_role = { character = GER_werner_von_fritsch advisor = { slot = army_chief idea_token = mod1440_chk_fritsch_army_chief cost = 0 } activate = yes }
	}
	log = "MOD1440 e7 hire: army chief [?army_chief.GetName], political advisors [?political_advisor^num], high command [?high_command^num]"
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


H_SERIES = 40          # D9: the figures National Figures writes down (tools/build_managers.py, SERIES)
H_DEEP = list(range(20, 27)) + list(range(33, 39))  # the resource balances and (D9) the equipment balances: below zero too
H_D9 = 31              # D9: the series a save of the build before D9 has (0 to 30)


def series_value(n):
    """The made-up value of series n in a month: a rising figure, a falling one and a wave, by turns; the balances
    and political power (D9) a wave around zero; the game's casualties (10), the total of every war (31), the dead of
    the month (32) and surrender progress (39) from two made-up wars (D9)."""
    if n == 10:
        return "cas_g"
    if n == 31:
        return "cas_t"
    if n == 32:
        return "cas_m"
    if n == 39:
        return "sur"
    if n in H_DEEP or n == 11:
        return "below"
    return ("up", "down", "wave")[n % 3]


def history_months(name, months, years, filled=H_SERIES):
    """An effect that fills the arrays of the History page with made-up months, without running time. years: with
    the year of each month, or without as a game saved before 2026-10-12 has them. filled: how many of the figures
    get months; 12 leaves the eight of 2026-10-16, the eleven of 2026-10-17 and the nine of D9 empty, as a game saved
    by the build before 2026-10-16 has them, 20 the eleven and the nine, as a save of 2026-10-16, 31 the nine of D9,
    as a save of the build before D9 (the drawing pads them, and back-fills 31 and 32 from series 10).
    D9: two made-up wars, months 40 to 69 and 100 on (of 130): the dead of each month in cas_m; the game's number
    (series 10) adds them during a war and drops to 0 when the first war ends, as casualties_k does; the total (31)
    never falls; surrender progress rises during the wars. A save with all 40 figures gets mod1440_h_cas_ver and the
    counters of the daily step; an older one loses them, so that the drawing back-fills."""
    series = "".join("\t\tadd_to_array = { mod1440_h_%d = %s }\n" % (n, series_value(n)) for n in range(filled))
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
    if filled == H_SERIES:
        counters = """	set_variable = { mod1440_h_cas_sum = cas_t }
	set_variable = { mod1440_h_cas_mon = 0 }
	set_variable = { mod1440_h_cas_last = casualties_k }
	set_variable = { mod1440_h_cas_from = global.date }
	set_variable = { mod1440_h_cas_ver = 1 }
"""
    else:
        counters = """	clear_variable = mod1440_h_cas_ver
	clear_variable = mod1440_h_cas_sum
	clear_variable = mod1440_h_cas_mon
	clear_variable = mod1440_h_cas_last
	clear_variable = mod1440_h_cas_from
"""
    return """
%s = {
%s	clear_array = mod1440_h_date
	clear_array = mod1440_h_year
	set_temp_variable = { cas_g = 0 }
	set_temp_variable = { cas_t = 0 }
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
		set_temp_variable = { cas_m = 0 }
		set_temp_variable = { sur = 0 }
		if = {
			limit = { check_variable = { t > 39 } check_variable = { t < 70 } }
			set_temp_variable = { cas_m = wave }
			set_temp_variable = { sur = t }
			subtract_from_temp_variable = { sur = 40 }
		}
		if = {
			limit = { check_variable = { t > 99 } }
			set_temp_variable = { cas_m = wave }
			multiply_temp_variable = { cas_m = 2 }
			set_temp_variable = { sur = t }
			subtract_from_temp_variable = { sur = 100 }
			multiply_temp_variable = { sur = 2 }
		}
		add_to_temp_variable = { cas_g = cas_m }
		add_to_temp_variable = { cas_t = cas_m }
		if = {
			limit = { check_variable = { t = 70 } }
			set_temp_variable = { cas_g = 0 }
		}
		if = {
			limit = { check_variable = { t = 0 } }
			set_temp_variable = { cas_m = -1 }
		}
%s		add_to_array = { mod1440_h_date = global.date }
%s		if = {
			limit = { check_variable = { mod1440_h_date^num > 120 } }
%s			remove_from_array = { array = mod1440_h_date index = 0 }
%s		}
	}
%s	mod1440_h_draw = yes
	log = "MOD1440 check: history filled, [?mod1440_h_date^num] months, [?mod1440_h_0^num] values, [?mod1440_h_year^num] years"
	log = "MOD1440 check: casualties, series 10 now [?cas_g] (the first war's dead dropped at month 70), total [?mod1440_h_cas_sum] in [?mod1440_h_31^num] months, month [?mod1440_h_32^num] months, worst [?mod1440_h_cas_worst], cas_ver [?mod1440_h_cas_ver]"
}
""" % (name, clear, months, series, year, forget, forget_year, counters)


# 130 months with years (the oldest ten are forgotten), the same as an older save has them, seven months, and
# 130 months of the twelve figures a save of the build before 2026-10-16 has, of the twenty of 2026-10-16 and (D9) of
# the 31 of the build before D9: then the drawing back-fills series 31 and 32 from series 10
HISTORY = ("\n# ---- the History page: made-up months\n"
           + history_months("mod1440_chk_months", 130, True) + history_months("mod1440_chk_months_old", 130, False)
           + history_months("mod1440_chk_months_few", 7, True) + history_months("mod1440_chk_months_twelve", 130, True, 12)
           + history_months("mod1440_chk_months_twenty", 130, True, 20) + history_months("mod1440_chk_months_d4", 130, True, H_D9))

# --- D9 ---
# The daily casualty step and the Equipment table, as Germany on 1 January 1936 (no war: casualties_k is 0).
HISTORY += """
# ---- National Figures, D9

# As if the game's casualties had risen by 12 thousand since yesterday: the step adds 12.0K to the total and to the
# month so far.
mod1440_chk_cas_rise = {
	set_variable = { mod1440_h_cas_last = casualties_k }
	subtract_from_variable = { mod1440_h_cas_last = 12 }
	mod1440_h_cas_step = yes
	mod1440_h_draw = yes
	log = "MOD1440 check: cas rise, total [?mod1440_h_cas_sum] month [?mod1440_h_cas_mon] game [?casualties_k] last [?mod1440_h_cas_last]"
}

# As if a war had ended since yesterday: the game's number 50 thousand lower. The step adds nothing.
mod1440_chk_cas_fall = {
	set_variable = { mod1440_h_cas_last = casualties_k }
	add_to_variable = { mod1440_h_cas_last = 50 }
	mod1440_h_cas_step = yes
	mod1440_h_draw = yes
	log = "MOD1440 check: cas fall, total [?mod1440_h_cas_sum] month [?mod1440_h_cas_mon] game [?casualties_k] last [?mod1440_h_cas_last]"
}

# The back-fill after mod1440_chk_months_d4, written to game.log.
mod1440_chk_backfill = {
	mod1440_h_draw = yes
	log = "MOD1440 check: backfill, cas_ver [?mod1440_h_cas_ver] months [?mod1440_h_date^num] series 10 [?mod1440_h_10^num] 31 [?mod1440_h_31^num] 32 [?mod1440_h_32^num] 33 [?mod1440_h_33^num] total [?mod1440_h_cas_sum] worst [?mod1440_h_cas_worst] from [?mod1440_h_cas_from.GetDateStringNoHourLong]"
}

# A made-up shortage in the Equipment table until the next day's count: infantry equipment 12.4K short with none in
# stock, towed anti-aircraft 1.1K short.
mod1440_chk_equip_short = {
	set_variable = { mod1440_nf_eq_s_0 = 0 }
	set_variable = { mod1440_nf_eq_d_0 = 12.4 }
	set_variable = { mod1440_nf_eq_b_0 = -12.4 }
	set_variable = { mod1440_nf_eq_s_4 = 0 }
	set_variable = { mod1440_nf_eq_d_4 = 1.1 }
	set_variable = { mod1440_nf_eq_b_4 = -1.1 }
	log = "MOD1440 check: equip short, infantry [?mod1440_nf_eq_b_0] anti-air [?mod1440_nf_eq_b_4]"
}

# The real count of the Equipment table, written to game.log beside the game's own numbers.
mod1440_chk_equip = {
	mod1440_nf_equip = yes
	log = "MOD1440 check: equip, infantry stock [?num_equipment@infantry_equipment] field [?num_equipment_in_armies@infantry_equipment] need [?num_target_equipment_in_armies@infantry_equipment]: [?mod1440_nf_eq_s_0] [?mod1440_nf_eq_d_0] [?mod1440_nf_eq_b_0]; trucks [?mod1440_nf_eq_s_5] [?mod1440_nf_eq_d_5] [?mod1440_nf_eq_b_5]"
}

# Political power below zero: the Now of its row in red with its sign.
mod1440_chk_pp_negative = {
	add_political_power = -200
}
"""
# --- end D9 ---


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

# --- E1 ---
# The War Diary after the UX review (2026-10-22): the new kinds of line, as Germany on 1 January 1936.
HISTORY += """
# ---- War Diary, E1 review

# Niederschlesien handed over to Austria and received back, with no war: "Handed over to", "Received from", and the
# state card's treaty wording.
mod1440_chk_treaty = {
	AUS = { set_state_controller = 66 }
	set_state_controller = 66
}

# The four states of Austria received on one day: one row "+3 states" in All, four lines under Territory.
mod1440_chk_treaty_run = {
	set_state_controller = 4
	set_state_controller = 152
	set_state_controller = 153
	set_state_controller = 976
}

# A skill level for the third general of the game's list: the line carries the level reached.
mod1440_chk_level = {
	set_temp_variable = { c_g = army_leaders^2 }
	var:c_g = { add_skill_level = 1 }
	log = "MOD1440 check: level, [?c_g.GetName] now at [?c_g.skill_level]"
}

# Poland's cipher broken at once (on_fully_decrypted_cipher, if the full ratio fires it).
mod1440_chk_cipher = {
	add_decryption = { target = POL ratio = 1 }
}

# Poland's government goes into exile in Germany: "Hosting the exiled government of" Poland.
mod1440_chk_exile = {
	POL = { become_exiled_in = { target = GER } }
}

# As a save of a build before the review: no number on the lines, no seen line, no marks of officers gone, no
# casualty step. Then the Records opened: every line gets n = 0, none stands on the lighter band, no officer gone
# before gets a line.
mod1440_chk_old3 = {
	clear_array = mod1440_ev_n
	clear_array = mod1440_tr_n
	clear_array = mod1440_kp_n
	clear_variable = mod1440_rec_v
	clear_variable = mod1440_of_gone_v
	clear_variable = mod1440_ev_cas_v
	mod1440_chk_sizes3 = yes
}

# How long the number part is beside the dates, and the review's other values.
mod1440_chk_sizes3 = {
	log = "MOD1440 check: sizes3 ev [?mod1440_ev_date^num]/[?mod1440_ev_n^num] tr [?mod1440_tr_date^num]/[?mod1440_tr_n^num] kp [?mod1440_kp_date^num]/[?mod1440_kp_n^num] seen [?mod1440_rec_seen] next [?mod1440_ln_next] new [?mod1440_rec_new]/[?mod1440_rec_new_war] cas [?mod1440_ev_cas_i] ([?casualties_k]k) gone [?mod1440_of_gone_v]"
}
"""
# --- end E1 ---

# --- D10 ---
# The population history of every state (the States page's Population view), as Germany on 1 January 1936: made-up
# months for every state without running time, a state taken in month 45 of them, a save without months, and the time
# of the monthly round over every state, paused. Each draws the page again when it is open.
POP_REDRAW = "    if = {\n        limit = { check_variable = { mod1440_st_open = 1 } }\n        mod1440_st_list = yes\n    }\n"
HISTORY += ("""
# ---- States, D10: the population history

# 120 made-up months for every state: the date of each is today's (a date cannot be made up), the year and the day
# number those of a month before today (30 days a month), the oldest in January 1936. Each state stands still for
# 45 months and then falls by 0.05% to 0.45% of today's population a month (by its population modulo 9), to today's
# number in the newest month, so that In a year differs from state to state.
mod1440_chk_pop_months = {
    clear_array = global.mod1440_pop_date
    clear_array = global.mod1440_pop_year
    clear_array = global.mod1440_pop_days
    for_loop_effect = {
        start = 0
        end = 120
        value = t
        add_to_array = { global.mod1440_pop_date = global.date }
        set_temp_variable = { mo = t }
        modulo_temp_variable = { mo = 12 }
        set_temp_variable = { yr = t }
        subtract_from_temp_variable = { yr = mo }
        divide_temp_variable = { yr = 12 }
        add_to_temp_variable = { yr = 1936 }
        add_to_array = { global.mod1440_pop_year = yr }
        set_temp_variable = { dn = t }
        subtract_from_temp_variable = { dn = 119 }
        multiply_temp_variable = { dn = 30 }
        add_to_temp_variable = { dn = global.num_days }
        add_to_array = { global.mod1440_pop_days = dn }
    }
    set_variable = { global.mod1440_pop_day = global.num_days }
    every_state = {
        clear_array = mod1440_pop_k
        set_temp_variable = { s = state_population_k }
        modulo_temp_variable = { s = 9 }
        add_to_temp_variable = { s = 1 }
        multiply_temp_variable = { s = 0.0005 }
        for_loop_effect = {
            start = 0
            end = 120
            value = t
            set_temp_variable = { f = 119 }
            subtract_from_temp_variable = { f = t }
            if = {
                limit = { check_variable = { t < 45 } }
                set_temp_variable = { f = 74 }
            }
            multiply_temp_variable = { f = s }
            add_to_temp_variable = { f = 1 }
            set_temp_variable = { v = state_population_k }
            multiply_temp_variable = { v = f }
            add_to_array = { mod1440_pop_k = v }
        }
        mod1440_pop_year = yes
    }
""" + POP_REDRAW + """    64 = {
        log = "MOD1440 check: pop months, [?global.mod1440_pop_date^num] months, Brandenburg [?mod1440_pop_k^num] values, first [?mod1440_pop_k^0] last [?mod1440_pop_k^119] now [?state_population_k], in a year [?mod1440_pop_dy]% (fall [?mod1440_pop_fall], has [?mod1440_pop_hy])"
    }
}

# Brandenburg (64) taken from Poland between month 44 and month 45 of the made-up months (needs mod1440_chk_pop_months):
# the first 45 columns in the preparing colour, the line at the 46th, Yours since the day.
mod1440_chk_pop_taken = {
    POL = {
        64 = {
            set_variable = { mod1440_sr_from = PREV }
        }
    }
    64 = {
        set_variable = { mod1440_sr_day = global.num_days }
        subtract_from_variable = { mod1440_sr_day = 2235 }
        set_variable = { mod1440_sr_date = global.date }
        log = "MOD1440 check: pop taken, Brandenburg day [?mod1440_sr_day], today [?global.num_days]"
    }
""" + POP_REDRAW + """}

# As a save of a build before D10: no month for any state, no stamp of the last round.
mod1440_chk_pop_clear = {
    clear_array = global.mod1440_pop_date
    clear_array = global.mod1440_pop_year
    clear_array = global.mod1440_pop_days
    clear_variable = global.mod1440_pop_day
    every_state = {
        clear_array = mod1440_pop_k
        clear_variable = mod1440_pop_dy
        clear_variable = mod1440_pop_fall
        clear_variable = mod1440_pop_hy
        clear_variable = mod1440_pop_ya
        clear_variable = mod1440_pop_last
    }
""" + POP_REDRAW + """    log = "MOD1440 check: pop clear, [?global.mod1440_pop_date^num] months"
}

# The monthly round once, as the first of a month would run it (the stamp put back), paused: game.log gives the time
# of the line before and after it. A month is added for every state.
mod1440_chk_pop_round = {
    log = "MOD1440 check: pop round begins, [?global.mod1440_pop_date^num] months"
    set_variable = { global.mod1440_pop_day = 0 }
    mod1440_pop_round = yes
    log = "MOD1440 check: pop round ends, [?global.mod1440_pop_date^num] months"
""" + POP_REDRAW + """}

# Ten months of the round without its guard, for a time game.log can measure in seconds.
mod1440_chk_pop_round10 = {
    log = "MOD1440 check: pop ten rounds begin, [?global.mod1440_pop_date^num] months"
    for_loop_effect = {
        start = 0
        end = 10
        value = t
        mod1440_pop_month = yes
    }
    log = "MOD1440 check: pop ten rounds end, [?global.mod1440_pop_date^num] months"
""" + POP_REDRAW + """}

# The guard: the round twice on one day writes one month (the stamp put back first, as the first of a month would).
mod1440_chk_pop_twice = {
    log = "MOD1440 check: pop twice begins, [?global.mod1440_pop_date^num] months"
    set_variable = { global.mod1440_pop_day = 0 }
    mod1440_pop_round = yes
    mod1440_pop_round = yes
    log = "MOD1440 check: pop twice ends, [?global.mod1440_pop_date^num] months (one more), stamp [?global.mod1440_pop_day] today [?global.num_days]"
""" + POP_REDRAW + """}
""").replace("    ", "\t")
# --- end D10 ---

# --- E4 round 2 ---
# The Wars page after its redesign (2026-10-29), as Germany on 1 January 1936: a war of several enemies on one side, both
# sides' dead from casualties_inflicted_by, a change of head of government during and after a war, and a save of the
# build before (its rows without wars, dead and leaders). The new parts of a row are tools/build_records.py's.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_records import WR_NEW_3, WO_NEW_3, WR_PARTS  # noqa: E402


def wars_row_log(table, extra):
    """A line of game.log for every row of a table of the wars: its war, how it began, its dead, its heads."""
    return ("\tfor_loop_effect = {\n\t\tstart = 0\n\t\tend = mod1440_%s_enemy^num\n\t\tvalue = c_i\n" % table
            + "\t\tset_temp_variable = { c_v = mod1440_%s_enemy^c_i }\n" % table + extra
            + '\t\tlog = "MOD1440 wr: %s [?c_v.GetTag] id [?mod1440_%s_id^c_i] grp [?mod1440_%s_grp^c_i] how [?mod1440_%s_how^c_i] '
              'role [?mod1440_chk_role] kus [?mod1440_%s_kus^c_i] kthem [?mod1440_%s_kthem^c_i] now ours [?mod1440_chk_k1] theirs [?mod1440_chk_k2] '
              'kday [?mod1440_%s_kday^c_i] lu0 [?mod1440_%s_lu0^c_i.GetName] lt0 [?mod1440_%s_lt0^c_i.GetName] lt1 [?mod1440_%s_lt1^c_i.GetName] '
              'gt1 [?mod1440_%s_gt1^c_i]"\n' % ((table,) * 11)
            + "\t}\n")


READ_NOW = """\t\tset_variable = { mod1440_chk_k1 = -1 }
\t\tset_variable = { mod1440_chk_k2 = -1 }
\t\tset_variable = { mod1440_chk_role = 0 }
\t\tif = { limit = { has_offensive_war_with = var:c_v } set_variable = { mod1440_chk_role = 1 } }
\t\tif = {
\t\t\tlimit = { var:c_v = { exists = yes } }
\t\t\tset_variable = { mod1440_wr_kv = ROOT }
\t\t\tset_variable = { mod1440_wr_ko = c_v }
\t\t\tset_temp_variable = { kr_prev = 0 }
\t\t\tmod1440_wr_kread = yes
\t\t\tset_variable = { mod1440_chk_k1 = kr }
\t\t\tset_variable = { mod1440_wr_kv = c_v }
\t\t\tset_variable = { mod1440_wr_ko = ROOT }
\t\t\tset_temp_variable = { kr_prev = 0 }
\t\t\tmod1440_wr_kread = yes
\t\t\tset_variable = { mod1440_chk_k2 = kr }
\t\t}
"""

HISTORY += """
# ---- Wars, E4 round 2

# The United Kingdom and France join Poland's side of the war Germany declared (mod1440_chk_war first): one war of three
# enemies on the page (has_war_together_with, has_offensive_war_with).
mod1440_chk_ally_join = {
\tENG = { add_to_war = { targeted_alliance = POL enemy = GER hostility_reason = asked_to_join } }
\tFRA = { add_to_war = { targeted_alliance = POL enemy = GER hostility_reason = asked_to_join } }
}

# Every row of the wars: its war (grp), how it began, our role (1: our offensive war), the dead kept and read now from
# zero (casualties_inflicted_by both ways, in thousands), the day the count began, the heads of government kept.
mod1440_chk_wr_log = {
\tlog = "MOD1440 wr: rows of today [?mod1440_wr_enemy^num], finished [?mod1440_wo_enemy^num], casualties_k [?casualties_k], all wars [?mod1440_h_cas_sum], inflicted [?mod1440_wr_kthem_all]"
""" + wars_row_log("wr", READ_NOW) + wars_row_log("wo", READ_NOW) + """}

# 100 full readings of the first enemy's dead (from zero each time), between two lines of game.log.
mod1440_chk_kread_time = {
\tlog = "MOD1440 wr: kread start"
\tfor_loop_effect = {
\t\tstart = 0
\t\tend = 100
\t\tvalue = c_n
\t\tset_variable = { mod1440_wr_kv = ROOT }
\t\tset_variable = { mod1440_wr_ko = mod1440_wr_enemy^0 }
\t\tset_temp_variable = { kr_prev = 0 }
\t\tmod1440_wr_kread = yes
\t}
\tlog = "MOD1440 wr: kread 100 readings done, last [?mod1440_wr_kn]"
}

# Poland's head of government retired during the war: the next day its row keeps the one of the first day (lt0) and the
# new one (lt1).
mod1440_chk_leader_change = {
\tPOL = { retire_country_leader = yes }
}

# Our head of government retired (after a war ended): a finished war keeps ours of its last day.
mod1440_chk_leader_change_us = {
\tretire_country_leader = yes
}

# As a save of the build before E4 round 2: the rows without their wars, dead and leaders. Then the Records opened (or a
# day run): mod1440_wr_grow gives them back.
mod1440_chk_old4 = {
""" + "".join("\tclear_array = mod1440_wr_%s\n" % part for part in WR_NEW_3) + "".join("\tclear_array = mod1440_wo_%s\n" % part for part in WO_NEW_3) + """\tmod1440_chk_sizes4 = yes
}

# E4 fix round 1: a row against the country itself. First the guard: mod1440_wr_open refuses it ("no war row for GER
# against itself" in game.log, the count unchanged). Then a row written past the guard, as a save might hold one, and the
# once-per-save repair of mod1440_wr_grow drops it ("a row of wr against the country itself was dropped").
mod1440_chk_self_row = {
\tlog = "MOD1440 check: self row, before: wr [?mod1440_wr_enemy^num] wars [?mod1440_wr_wars]"
\tset_temp_variable = { wr_c = THIS }
\tset_temp_variable = { wr_old = 0 }
\tset_temp_variable = { wr_how = 1 }
\tmod1440_wr_open = yes
\tlog = "MOD1440 check: self row, after the guard: wr [?mod1440_wr_enemy^num] wars [?mod1440_wr_wars]"
""" + "".join("\tadd_to_array = { mod1440_wr_%s = %s }\n" % (part, "THIS" if part == "enemy" else ("global.num_days" if part in ("day0", "kday") else ("global.date" if part == "since" else 0)))
              for part in WR_PARTS) + """\tlog = "MOD1440 check: self row, written past the guard: wr [?mod1440_wr_enemy^num]"
\tclear_variable = mod1440_wr_fix1
\tmod1440_wr_grow = yes
\tlog = "MOD1440 check: self row, after the repair: wr [?mod1440_wr_enemy^num] wars [?mod1440_wr_wars]"
}

# E4 fix round 1: the user's save showed an enemy with the player's own name and flag that joined a war and was annexed
# on its last day: most likely the other side of a civil war (a country of its own that keeps the name and flag). A
# civil war in Germany, then mod1440_chk_civil_log the next day: the rebels' tag, name, original tag and whether they
# are a dynamic country, beside the player's.
mod1440_chk_civil_war = {
\tstart_civil_war = { ideology = communism size = 0.3 }
}

mod1440_chk_civil_log = {
\tlog = "MOD1440 check: civil, the player [This.GetTag] [This.GetName]"
\tfor_each_loop = {
\t\tarray = mod1440_wr_enemy
\t\tvalue = c_v
\t\tset_variable = { mod1440_chk_dyn = 0 }
\t\tif = { limit = { var:c_v = { is_dynamic_country = yes } } set_variable = { mod1440_chk_dyn = 1 } }
\t\tlog = "MOD1440 check: civil, enemy [?c_v.GetTag] [?c_v.GetName] dynamic [?mod1440_chk_dyn]"
\t}
}

# How long every new part is beside the rows.
mod1440_chk_sizes4 = {
\tlog = "MOD1440 check: sizes4 wr [?mod1440_wr_enemy^num]: """ + " ".join("%s [?mod1440_wr_%s^num]" % (p, p) for p in WR_NEW_3) + """"
\tlog = "MOD1440 check: sizes4 wo [?mod1440_wo_enemy^num]: """ + " ".join("%s [?mod1440_wo_%s^num]" % (p, p) for p in WO_NEW_3) + """"
}
"""
# --- end E4 round 2 ---

# --- E2 round 2 ---
# The Officers page after its redesign (2026-10-30). As Germany: the chain of command by both methods, a battle counted
# for a field marshal, and the values the page reads (num_assigned_traits, num_max_traits, a free trait slot,
# is_promoted_from_unit, num_armored, the battle plans). A marshal leading an army group is made by hand in the game
# (two armies, create an army group, assign a field marshal); run the daily round once (or click Order of battle).
E2_OWNERS = ("GER", "AUS", "CZE", "POL", "HOL", "BEL", "LUX", "FRA", "DEN", "SWI")      # where Germany's armies stand in a check


def e2_provinces():
    """{state id: [provinces]} of the states the game's history gives to E2_OWNERS; {} without the game."""
    import glob
    import re
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import guiparse
        game = guiparse.find_game_dir()
    except Exception:
        game = None
    out = {}
    for path in sorted(glob.glob(os.path.join(game or "-", "history", "states", "*.txt"))):
        text = re.sub(r"#[^\n]*", "", io.open(path, encoding="utf-8-sig", errors="replace").read())
        sid = re.search(r"\bid\s*=\s*(\d+)", text)
        owner = re.search(r"\bowner\s*=\s*(\w+)", text)
        provinces = re.search(r"\bprovinces\s*=\s*\{([^}]*)\}", text)
        if sid and owner and provinces and owner.group(1) in E2_OWNERS:
            out[int(sid.group(1))] = [int(p) for p in provinces.group(1).split()]
    return out


def e2_effects():
    states = e2_provinces()
    which = "".join("\t\t\t\t%sif = { limit = { state = %d } set_temp_variable = { chk_sid = %d } }\n" % ("" if n == 0 else "else_", s, s)
                    for n, s in enumerate(sorted(states)))
    tests = ""
    for n, (s, provinces) in enumerate(sorted(states.items())):
        body = ""
        for p in provinces:
            body += ("\t\t\t\tif = { limit = { is_leading_army_in_province = %d } log = \"MOD1440 e2 oob: province %d general [THIS.GetName] yes\"\n"
                     "\t\t\t\t\tset_temp_variable = { chk_p = %d }\n"
                     "\t\t\t\t\tPREV = { every_army_leader = { limit = { is_leading_army_group = yes }\n"
                     "\t\t\t\t\t\tif = { limit = { is_leading_army_in_province = { province = %d include_field_marshal = yes } } "
                     "log = \"MOD1440 e2 oob: province %d marshal [THIS.GetName] yes (literal)\" }\n"
                     "\t\t\t\t\t\tif = { limit = { is_leading_army_in_province = { province = var:chk_p include_field_marshal = yes } } "
                     "log = \"MOD1440 e2 oob: province %d marshal [THIS.GetName] yes (var:)\" }\n"
                     "\t\t\t\t\t} }\n\t\t\t\t}\n" % (p, p, p, p, p, p))
        tests += "\t\t\t%sif = { limit = { check_variable = { chk_sid = %d } }\n%s\t\t\t}\n" % ("" if n == 0 else "else_", s, body)
    return """
# The chain of command, both methods, for every general who leads an army with troops: his state (Army Readiness's
# mod1440_al_loc) and count; each marshal leading an army group asked num_units_in_state there (the state method) and
# the province trigger on each province of that state where the general leads (the province method), literal and var:.
mod1440_chk_e2_oob = {
\tmod1440_ar_count = yes
\tlog = "MOD1440 e2 oob: start [?global.date.GetDateStringNoHourLong]"
\tevery_army_leader = {
\t\tlimit = { is_leading_army_group = yes }
\t\tlog = "MOD1440 e2 oob: marshal [THIS.GetName] leads an army group, num_units [?num_units] num_units_in_state@loc [?num_units_in_state@var:mod1440_al_loc] loc [?mod1440_al_loc.GetName]"
\t}
\tevery_army_leader = {
\t\tlimit = { NOT = { is_leading_army_group = yes } check_variable = { num_units > 0 } }
\t\tset_temp_variable = { chk_s = mod1440_al_loc }
\t\tset_temp_variable = { chk_n = mod1440_al_lcnt }
\t\tlog = "MOD1440 e2 oob: general [THIS.GetName] num_units [?num_units] state [?chk_s.GetName] count [?chk_n]"
\t\tPREV = {
\t\t\tevery_army_leader = {
\t\t\t\tlimit = { is_leading_army_group = yes }
\t\t\t\tlog = "MOD1440 e2 oob:   marshal [THIS.GetName] num_units_in_state there [?num_units_in_state@var:chk_s] (state method: links if >= [?chk_n])"
\t\t\t}
\t\t}
\t\tset_temp_variable = { chk_sid = 0 }
\t\tif = {
\t\t\tlimit = { check_variable = { chk_n > 0 } }
\t\t\tvar:chk_s = {
""" + which + """\t\t\t}
""" + tests + """\t\t}
\t\tlog = "MOD1440 e2 oob:   state id [?chk_sid] (0: not among the states this effect knows)"
\t}
\tmod1440_of_chain = yes
\tmod1440_chk_e2_log = yes
}

# A battle counted for a field marshal: a won and a lost battle of the first general linked to a marshal, through the
# hooks' own effects (on_army_leader_won_combat and _lost_combat call them under the human check).
mod1440_chk_e2_battle = {
\tset_temp_variable = { chk_done = 0 }
\tevery_army_leader = {
\t\tlimit = { check_variable = { mod1440_of_fm_n > 0 } check_variable = { chk_done = 0 } }
\t\tset_temp_variable = { chk_done = 1 }
\t\tlog = "MOD1440 e2 battle: [THIS.GetName] under [?mod1440_of_fm.GetName]"
\t\tvar:mod1440_of_fm = { log = "MOD1440 e2 battle: marshal [THIS.GetName] before gwon [?mod1440_of_gwon] glost [?mod1440_of_glost]" }
\t\tmod1440_of_g_won = yes
\t\tmod1440_of_g_lost = yes
\t\tvar:mod1440_of_fm = { log = "MOD1440 e2 battle: marshal [THIS.GetName] after gwon [?mod1440_of_gwon] glost [?mod1440_of_glost]" }
\t}
\tif = { limit = { check_variable = { chk_done = 0 } } log = "MOD1440 e2 battle: no general is linked to a marshal (run mod1440_chk_e2_oob first)" }
}

# What the page reads of every leader, and his link.
mod1440_chk_e2_log = {
\tevery_army_leader = {
\t\tset_temp_variable = { chk_can = 0 }
\t\tif = { limit = { check_variable = { num_assigned_traits < num_max_traits } } set_temp_variable = { chk_can = 1 } }
\t\tset_temp_variable = { chk_div = 0 }
\t\tif = { limit = { is_promoted_from_unit = yes } set_temp_variable = { chk_div = 1 } }
\t\tlog = "MOD1440 e2 leader: [THIS.GetName] fm [?mod1440_of_fm.GetName] fm_n [?mod1440_of_fm_n] subs [?mod1440_of_subs^num] gwon [?mod1440_of_gwon] glost [?mod1440_of_glost] assigned [?num_assigned_traits] max [?num_max_traits] traits [?num_traits] can_select [?chk_can] from_division [?chk_div] div [?num_units] armoured [?num_armored] plans [?num_battle_plans] planning [?avg_unit_planning_ratio] entrenchment [?avg_unit_entrenchment_ratio] eq [?mod1440_al_eq] hq [?mod1440_al_hq.GetName]"
\t}
\tevery_navy_leader = {
\t\tset_temp_variable = { chk_can = 0 }
\t\tif = { limit = { check_variable = { num_assigned_traits < num_max_traits } } set_temp_variable = { chk_can = 1 } }
\t\tlog = "MOD1440 e2 leader: [THIS.GetName] (admiral) assigned [?num_assigned_traits] max [?num_max_traits] can_select [?chk_can] ships [?num_ships]"
\t}
}
"""


HISTORY += e2_effects()
# --- end E2 round 2 ---


# --- E2b ---
# The exact chain of command on a game with the Modding Manager's field marshal patch (SCR-086): every army leader's
# has_orders_group as an integer (the patch gives the army group's id x 0.00001; unpatched it is 1 or 0), whether he leads
# an army group, the link the chain made, and mod1440_of_exact. Run mod1440_of_chain first (it runs once a day).
HISTORY += """
mod1440_chk_e2b_log = {
	mod1440_of_chain = yes
	log = "MOD1440 e2b: exact [?mod1440_of_exact] how [?mod1440_of_chain_how.GetTokenKey]"
	every_army_leader = {
		set_temp_variable = { chk_o = has_orders_group }
		multiply_temp_variable = { chk_o = 100000 }
		set_temp_variable = { chk_g = 0 }
		if = { limit = { is_leading_army_group = yes } set_temp_variable = { chk_g = 1 } }
		log = "MOD1440 e2b: [THIS.GetName] has_orders_group x100000 [?chk_o|0] raw [?has_orders_group|5] army_group [?chk_g] divisions [?num_units] fm [?mod1440_of_fm.GetName] fm_n [?mod1440_of_fm_n] subs [?mod1440_of_subs^num]"
	}
}
"""
# --- end E2b ---

# --- E3 round 2 ---
# The Government page (scratch/phases/E3): the elements of the political_advisor array (the "German Reich" seat), advisors
# hired and dismissed, a new head of government, an election, an agency with upgrades and an operative, and made-up months
# of party support over six years (mod1440_chk_months first: National Figures' 130 months, of which 120 are kept) with a
# change of the ruling party in the 50th shown month and a head of government of the other party from then on.
HISTORY += """
mod1440_chk_gv_phantom = {
	set_temp_variable = { chk_me = THIS }
	for_each_loop = {
		array = political_advisor
		index = chk_i
		value = chk_v
		set_temp_variable = { chk_t = chk_me }
		var:chk_v = { set_temp_variable = { chk_t = THIS } }
		set_temp_variable = { chk_root = 0 }
		if = { limit = { check_variable = { chk_t = chk_me } } set_temp_variable = { chk_root = 1 } }
		set_temp_variable = { chk_p = 0 }
		if = { limit = { OR = { check_variable = { chk_v > 5368 } check_variable = { chk_v < -21000 } } } set_temp_variable = { chk_p = 1 } }
		log = "MOD1440 gv phantom: i [?chk_i] value [?chk_v|5] name [?chk_v.GetName] scope_is_root [?chk_root] person [?chk_p] of [?political_advisor^num]"
	}
	log = "MOD1440 gv phantom: the page keeps [?mod1440_gv_adv^num] persons"
}

mod1440_chk_gv_hire = {
	mod1440_chk_hire = yes
}

mod1440_chk_gv_fire = {
	deactivate_advisor = konstantin_von_neurath
	deactivate_advisor = todt
}

mod1440_chk_gv_leader = {
	retire_country_leader = yes
}

mod1440_chk_gv_election = {
	hold_election = ROOT
	mod1440_gv_election = yes
}

mod1440_chk_gv_agency = {
	create_intelligence_agency = yes
	upgrade_intelligence_agency = upgrade_economy_civilian
	upgrade_intelligence_agency = upgrade_form_department
	create_operative_leader = { bypass_recruitment = yes available_to_spy_master = no }
	set_variable = { mod1440_gv_ag_has = 0 }
	mod1440_gv_daily = yes
	log = "MOD1440 gv agency: [?num_of_operatives] operatives, [?agency_upgrade_number] upgrades, done [?mod1440_gv_ag_done], cipher [?encryption_strength], defence [?cryptology_defense_level]"
}

mod1440_chk_gv_months = {
	mod1440_chk_gv_clear = yes
	set_temp_variable = { chk_n = mod1440_h_date^num }
	set_temp_variable = { chk_cut = chk_n }
	subtract_from_temp_variable = { chk_cut = 22 }
	set_temp_variable = { chk_f = 40 }
	for_loop_effect = {
		start = 0
		end = chk_n
		value = chk_k
		set_temp_variable = { chk_d = chk_k }
		multiply_temp_variable = { chk_d = 0.3 }
		set_temp_variable = { chk_f = 40 }
		add_to_temp_variable = { chk_f = chk_d }
		if = {
			limit = { check_variable = { chk_k > chk_cut } }
			set_temp_variable = { chk_f = 44 }
			set_temp_variable = { chk_e = chk_k }
			subtract_from_temp_variable = { chk_e = chk_cut }
			subtract_from_temp_variable = { chk_f = chk_e }
		}
		set_temp_variable = { chk_dm = 30 }
		subtract_from_temp_variable = { chk_dm = chk_d }
		clamp_temp_variable = { var = chk_dm min = 2 max = 40 }
		set_temp_variable = { chk_co = 5 }
		set_temp_variable = { chk_ne = 100 }
		subtract_from_temp_variable = { chk_ne = chk_f }
		subtract_from_temp_variable = { chk_ne = chk_dm }
		subtract_from_temp_variable = { chk_ne = chk_co }
		add_to_array = { mod1440_gv_pp_0 = chk_f }
		add_to_array = { mod1440_gv_pp_1 = chk_dm }
		add_to_array = { mod1440_gv_pp_2 = chk_co }
		add_to_array = { mod1440_gv_pp_3 = chk_ne }
		if = {
			limit = { check_variable = { chk_k > chk_cut } }
			add_to_array = { mod1440_gv_pp_g = 4 }
			add_to_array = { mod1440_gv_pp_h = mod1440_gv_rul^0 }
		}
		else = {
			add_to_array = { mod1440_gv_pp_g = 1 }
			add_to_array = { mod1440_gv_pp_h = country_leader }
		}
	}
	mod1440_gv_election = yes
	set_variable = { mod1440_gv_range = 0 }
	mod1440_gv_chart = yes
	log = "MOD1440 gv months: [?mod1440_gv_pp_0^num] months, [?mod1440_gv_pp_n] shown, the change of rule at [?chk_cut], [?mod1440_gv_el^num] elections"
}

mod1440_chk_gv_clear = {
""" + "".join("\tclear_array = mod1440_gv_pp_%s\n" % part for part in ("0", "1", "2", "3", "g", "h")) + """}
"""
# --- end E3 round 2 ---

# --- E7 probe ---
# Phase E7 (2026-10-29), step 1: does properties = { <icon> = { image = "portrait" } } draw the scope's unit leader
# portrait through the game's own portrait code (register SGUI-053, read in hoi4.exe 1.19.3, not yet seen in the game)?
# A throwaway window, mod1440_probe_portraits, written with --probe beside the check effects and removed with --restore.
# Nothing of it is in the output of tools/build_managers.py; the test suite fails while it is there (--check).
#
# Each cell: left the icon with image = "portrait" (own sprite GFX_portrait_unknown, like the pages), right the sprite
# the mod's table names (mod1440_p, tools/portraits_table.py), under them the row's name. The control row Z has the
# unknown woman as its own sprite: her outline there means the property left the icon alone, the man's outline means the
# portrait code drew its fallback, nothing means the text was taken as a sprite name nobody declares [SPR-017].

PROBE_WINDOW = "mod1440_probe_portraits"
PROBE_AT = (40, 80)
PROBE_SIZE = (2480, 1160)
PROBE_SCALE = 0.35                    # 55x74: a face is recognisable, and 17 cells fit a line
PROBE_SMALL = 0.22                    # the Officers list's portrait (34x46)
CELL = (140, 100)
CELL_SMALL = (200, 52)
CELL_FULL = (340, 240)
PROBE_FILES = {
    "gui": "interface/%s.gui" % PROBE_WINDOW,
    "script": "common/scripted_guis/%s.txt" % PROBE_WINDOW,
    "loc": "localisation/english/mod1440_probe_l_english.yml",
    "scene": "tools/scenes/probe_portraits.json",
}
# (list, label, array, entry container, x, y, columns, lines, label width, label text)
PROBE_LISTS = [
    ("a", "mod1440_pr_a", "mod1440_probe_cell", 16, 56, 17, 2, 2300,
     "A  every_army_leader, kept as the mod keeps him (mod1440_of_me): [?mod1440_pr_a^num] leaders"),
    ("b", "mod1440_of_rows", "mod1440_probe_cell", 16, 292, 17, 3, 2300,
     "B  the Officers page's own array mod1440_of_rows: [?mod1440_of_rows^num] rows"),
    ("d", "mod1440_pr_d", "mod1440_probe_cell", 16, 628, 6, 2, 820, "D  every_navy_leader: [?mod1440_pr_d^num]"),
    ("c", "mod1440_pr_c", "mod1440_probe_cell", 880, 628, 1, 1, 140, "C  one row"),
    ("e", "mod1440_pr_e", "mod1440_probe_cell", 1040, 628, 1, 2, 140, "E  made up"),
    ("f", "mod1440_pr_f", "mod1440_probe_cell", 1200, 628, 1, 1, 140, "F  head of gov."),
    ("h", "mod1440_pr_h", "mod1440_probe_cell", 1360, 628, 3, 2, 420, "H  command by effect: [?mod1440_pr_h^num]"),
    ("z", "mod1440_pr_z", "mod1440_probe_cell_ctl", 1800, 628, 3, 1, 420, "Z  control: own sprite the woman"),
    ("g2", "mod1440_pr_g2", "mod1440_probe_cell_full", 16, 864, 3, 1, 1000, "G  full size: C, E and the first of H"),
    ("g1", "mod1440_pr_g1", "mod1440_probe_cell_small", 1060, 864, 5, 2, 1000, "G  at 0.22 as in the Officers list: the first ten of A"),
]
PROBE_ARRAYS = ["mod1440_pr_" + name for name in ("a", "c", "d", "e", "f", "h", "z", "g1", "g2")]
PROBE_LOG = [("A", "mod1440_pr_a"), ("B", "mod1440_of_rows"), ("C", "mod1440_pr_c"), ("D", "mod1440_pr_d"),
             ("E", "mod1440_pr_e"), ("F", "mod1440_pr_f"), ("H", "mod1440_pr_h"), ("Z", "mod1440_pr_z"),
             ("G1", "mod1440_pr_g1"), ("G2", "mod1440_pr_g2")]
# H: characters of Germany with no command at the start, given one by effect, so unit leaders without a number kept by
# their place (Engine Facts X66, X67). Himmler: Road to 56 gives his army portrait as a texture file, the game a sprite;
# Bormann: a sprite; Canaris: no large army portrait (Road to 56: a civilian one as a file, which a general does not use).
PROBE_BY_EFFECT = ["GER_heinrich_himmler", "GER_martin_bormann", "GER_wilhelm_canaris"]
# C: one officer alone, Road to 56's Keitel (his army portrait is gfx/leaders/GER/r56_portrait_GER_Wilhelm_Keitel.dds)
PROBE_SINGLE = "GER_wilhelm_keitel"
SKILLS = "skill = 1 attack_skill = 1 defense_skill = 1 planning_skill = 1 logistics_skill = 1"


def probe_effects():
    """The check effects of the probe: fill its arrays, open and close it, log every row."""
    def logs(letter, array):
        return ("    for_each_loop = {\n        array = %s\n        value = pr_v\n        index = pr_i\n"
                "        var:pr_v = { log = \"MOD1440 probe %s [?pr_i]: [?pr_v.GetName], kept as [?pr_v], table [?mod1440_p.GetTokenKey]\" }\n"
                "    }\n" % (array, letter))
    text = """
# ---- E7 probe (2026-10-29): portraits by image = "portrait" [SGUI-053], window mod1440_probe_portraits (--probe).
# As Germany on 1 January 1936 with Road to 56 loaded (RT56 - VNR - UTT Standalone v16). In the game's own files the
# rows are the same people with the game's sprites.

# Fills the probe's arrays, opens its window and logs every row ("MOD1440 probe" in game.log). A second run makes no
# second general and gives no second command.
mod1440_chk_probe = {
    if = {
        limit = { NOT = { check_variable = { mod1440_pr_made = 1 } } }
        set_variable = { mod1440_pr_made = 1 }
        # E: a general the game makes up: no portraits block, so the portrait code picks one from the pools [CHR-011]
        every_army_leader = { set_variable = { mod1440_pr_old = 1 } }
        create_corps_commander = {
            name = "Probe General"
            %s
        }
        every_army_leader = {
            limit = { NOT = { check_variable = { mod1440_pr_old = 1 } } }
            set_variable = { mod1440_pr_gen = 1 }
        }
        # H: a command by effect: unit leaders without a number, kept by their place (X66, X67)
%s    }
    # the mod's own round: places for leaders without a number, the Officers page's list (B), the table's sprites
    mod1440_of_list = yes
%s    # A, E, H: every general as the mod keeps him, his number or his place
    every_army_leader = {
        mod1440_p_officer = yes
        mod1440_of_me = yes
        if = {
            limit = { NOT = { check_variable = { of_me = 0 } } }
            add_to_array = { PREV.mod1440_pr_a = of_me }
            if = { limit = { check_variable = { mod1440_pr_gen = 1 } } add_to_array = { PREV.mod1440_pr_e = of_me } }
            if = { limit = { check_variable = { of_me > 0 } } add_to_array = { PREV.mod1440_pr_h = of_me } }
        }
    }
    # D: every admiral
    every_navy_leader = {
        mod1440_p_officer = yes
        mod1440_of_me = yes
        if = {
            limit = { NOT = { check_variable = { of_me = 0 } } }
            add_to_array = { PREV.mod1440_pr_d = of_me }
        }
    }
    # C: one officer alone (the slot of an officer's file, a commander of a war): Keitel, else the first of A
    every_army_leader = {
        limit = { PREV = { has_character = %s } is_character = %s }
        mod1440_of_me = yes
        add_to_array = { PREV.mod1440_pr_c = of_me }
    }
    if = {
        limit = { check_variable = { mod1440_pr_c^num = 0 } check_variable = { mod1440_pr_a^num > 0 } }
        add_to_array = { mod1440_pr_c = mod1440_pr_a^0 }
    }
    # F: the head of government, a character with no command: expected to draw nothing [SGUI-053]
    set_temp_variable = { pr_ld = country_leader }
    var:pr_ld = {
        mod1440_p_leader = yes
        set_variable = { mod1440_p = p_tok }
    }
    add_to_array = { mod1440_pr_f = pr_ld }
    # Z: the control, on icons whose own sprite is the unknown woman: the first of A, E, F
    if = { limit = { check_variable = { mod1440_pr_a^num > 0 } } add_to_array = { mod1440_pr_z = mod1440_pr_a^0 } }
    if = { limit = { check_variable = { mod1440_pr_e^num > 0 } } add_to_array = { mod1440_pr_z = mod1440_pr_e^0 } }
    add_to_array = { mod1440_pr_z = pr_ld }
    # G: at full size C, E and the first of H; at 0.22 the first ten of A
    if = { limit = { check_variable = { mod1440_pr_c^num > 0 } } add_to_array = { mod1440_pr_g2 = mod1440_pr_c^0 } }
    if = { limit = { check_variable = { mod1440_pr_e^num > 0 } } add_to_array = { mod1440_pr_g2 = mod1440_pr_e^0 } }
    if = { limit = { check_variable = { mod1440_pr_h^num > 0 } } add_to_array = { mod1440_pr_g2 = mod1440_pr_h^0 } }
    for_each_loop = {
        array = mod1440_pr_a
        value = pr_v
        index = pr_i
        if = { limit = { check_variable = { pr_i < 10 } } add_to_array = { mod1440_pr_g1 = pr_v } }
    }
    set_variable = { mod1440_pr_open = 1 }
    add_to_variable = { mod1440_pr_dirty = 1 }
    mod1440_chk_probe_log = yes
}

# Every row of the probe in game.log: the list, its place in it, the name, what the array holds, the table's sprite.
mod1440_chk_probe_log = {
    log = "MOD1440 probe: [ROOT.GetTag], %s"
%s}

# The window drawn again (its dirty variable changed), for a second capture.
mod1440_chk_probe_redraw = {
    add_to_variable = { mod1440_pr_dirty = 1 }
}

mod1440_chk_probe_close = {
    set_variable = { mod1440_pr_open = 0 }
}
""" % (SKILLS,
       "".join("        if = { limit = { has_character = %s } add_corps_commander_role = { character = %s %s } }\n" % (c, c, SKILLS)
               for c in PROBE_BY_EFFECT),
       "".join("    clear_array = %s\n" % a for a in PROBE_ARRAYS),
       PROBE_SINGLE, PROBE_SINGLE,
       " ".join("%s [?%s^num]" % (letter, array) for letter, array in PROBE_LOG),
       "".join(logs(letter, array) for letter, array in PROBE_LOG))
    return text.replace("    ", "\t")


def probe_gui():
    """The probe's window and its four kinds of cell."""
    def icon(name, x, y, sprite, scale=None):
        return '\t\ticonType = { name = "%s" position = { x = %d y = %d } spriteType = "%s"%s }\n' % (
            name, x, y, sprite, " scale = %s" % scale if scale else "")

    def text(name, x, y, w, h, key, font="hoi_16mbs"):
        return ('\t\tinstantTextboxType = { name = "%s" position = { x = %d y = %d } font = "%s" text = "%s" maxWidth = %d '
                'maxHeight = %d format = left fixedsize = yes }\n' % (name, x, y, font, key, w, h))

    def cell(name, size, body):
        return ('\tcontainerWindowType = {\n\t\tname = "%s"\n\t\tposition = { x = 0 y = 0 }\n\t\tsize = { width = %d height = %d }\n%s\t}\n'
                % (name, size[0], size[1], body))

    face_w = int(round(156 * PROBE_SCALE))
    window = text("pr_title", 16, 14, 2300, 30, "MOD1440_PR_TITLE", "hoi_24header")
    window += ('\t\tbuttonType = { name = "pr_close" position = { x = %d y = 12 } quadTextureSprite = "GFX_closebutton" '
               'clicksound = click_default shortcut = "ESCAPE" }\n' % (PROBE_SIZE[0] - 60))
    sizes = {"mod1440_probe_cell": CELL, "mod1440_probe_cell_ctl": CELL, "mod1440_probe_cell_small": CELL_SMALL,
             "mod1440_probe_cell_full": CELL_FULL}
    for name, array, entry, x, y, cols, lines, label_w, label in PROBE_LISTS:
        slot = sizes[entry]
        window += text("pr_%s_l" % name, x, y, label_w, 24, "MOD1440_PR_%s" % name.upper(), "hoi_18mbs")
        window += ('\t\tgridboxtype = {\n\t\t\tname = "pr_%s_grid"\n\t\t\tposition = { x = %d y = %d }\n'
                   '\t\t\tsize = { width = %d height = %d }\n\t\t\tslotsize = { width = %d height = %d }\n'
                   '\t\t\tadd_horizontal = yes\n\t\t\tmax_slots_horizontal = %d\n\t\t\tformat = "UPPER_LEFT"\n\t\t}\n'
                   % (name, x, y + 26, cols * slot[0], lines * slot[1], slot[0], slot[1], cols))
    window += text("pr_legend", 1060, 1000, 1400, 120, "MOD1440_PR_LEGEND")
    out = ("# CHECK ONLY: written by tools/check_effects.py --probe (phase E7), removed with --restore.\nguiTypes = {\n"
           '\tcontainerWindowType = {\n\t\tname = "%s"\n\t\tposition = { x = %d y = %d }\n\t\tsize = { width = %d height = %d }\n'
           '\t\tbackground = { name = "Background" quadTextureSprite = "GFX_tiled_window_1b_thin_border" }\n%s\t}\n'
           % (PROBE_WINDOW, PROBE_AT[0], PROBE_AT[1], PROBE_SIZE[0], PROBE_SIZE[1], window))
    table_x = 4 + face_w + 7
    out += cell("mod1440_probe_cell", CELL, icon("pr_face", 4, 2, "GFX_portrait_unknown", PROBE_SCALE)
                + icon("pr_table", table_x, 2, "GFX_portrait_unknown", PROBE_SCALE) + text("pr_name", 2, 78, 136, 20, "MOD1440_PR_NAME"))
    out += cell("mod1440_probe_cell_ctl", CELL, icon("pr_face_ctl", 4, 2, "GFX_portrait_unknown_female", PROBE_SCALE)
                + icon("pr_table", table_x, 2, "GFX_portrait_unknown", PROBE_SCALE) + text("pr_name", 2, 78, 136, 20, "MOD1440_PR_NAME"))
    out += cell("mod1440_probe_cell_small", CELL_SMALL, icon("pr_face_s", 3, 3, "GFX_portrait_unknown", PROBE_SMALL)
                + text("pr_name_s", 42, 15, 154, 20, "MOD1440_PR_NAME"))
    out += cell("mod1440_probe_cell_full", CELL_FULL, icon("pr_face_f", 4, 2, "GFX_portrait_unknown")
                + icon("pr_table_f", 168, 2, "GFX_portrait_unknown") + text("pr_name_f", 4, 216, 330, 22, "MOD1440_PR_NAME", "hoi_18mbs"))
    return out + "}\n"


def probe_script():
    lists = "".join('\t\t\tpr_%s_grid = {\n\t\t\t\tarray = %s\n\t\t\t\tchange_scope = yes\n\t\t\t\tentry_container = "%s"\n\t\t\t}\n'
                    % (name, array, entry) for name, array, entry, *_ in PROBE_LISTS)
    portrait = "".join('\t\t\t%s = {\n\t\t\t\timage = "portrait"\n\t\t\t}\n' % w for w in ("pr_face", "pr_face_ctl", "pr_face_s", "pr_face_f"))
    table = "".join('\t\t\t%s = {\n\t\t\t\timage = "[?mod1440_p.GetTokenKey]"\n\t\t\t}\n' % w for w in ("pr_table", "pr_table_f"))
    return ("# CHECK ONLY: written by tools/check_effects.py --probe (phase E7), removed with --restore.\nscripted_gui = {\n"
            "\t%s = {\n\t\tcontext_type = player_context\n\t\twindow_name = \"%s\"\n\n"
            "\t\tvisible = {\n\t\t\tcheck_variable = { mod1440_pr_open = 1 }\n\t\t}\n\n\t\tdirty = mod1440_pr_dirty\n\n"
            "\t\teffects = {\n\t\t\tpr_close_click = {\n\t\t\t\tset_variable = { mod1440_pr_open = 0 }\n\t\t\t}\n\t\t}\n\n"
            "\t\tdynamic_lists = {\n%s\t\t}\n\n\t\tproperties = {\n%s%s\t\t}\n\n"
            "\t\tai_enabled = {\n\t\t\talways = no\n\t\t}\n\t}\n}\n" % (PROBE_WINDOW, PROBE_WINDOW, lists, portrait, table))


def probe_loc():
    texts = {
        "MOD1440_PR_TITLE": "E7 probe: image = portrait (left in each cell) beside the sprite of the mod's table (right). Throwaway: tools/check_effects.py --restore",
        "MOD1440_PR_NAME": "[THIS.GetName]",
        "MOD1440_PR_LEGEND": ("Left: an icon whose own sprite is the unknown leader, with image = portrait in the row's scope. Right: mod1440_p, "
                              "the sprite the mod's table names. Z has the unknown woman as its own sprite: her outline means the property "
                              "left the icon alone, the man's outline the portrait code's fallback, an empty slot a sprite name nobody declares."),
    }
    for name, _array, _entry, _x, _y, _cols, _lines, _w, label in PROBE_LISTS:
        texts["MOD1440_PR_%s" % name.upper()] = label
    return "﻿l_english:\n" + "".join(' %s:0 "%s"\n' % (k, v) for k, v in sorted(texts.items()))


def probe_scene():
    import json
    rows = {"pr_a_grid": 26, "pr_b_grid": 34, "pr_d_grid": 8, "pr_c_grid": 1, "pr_e_grid": 1, "pr_f_grid": 1, "pr_h_grid": 3,
            "pr_z_grid": 3, "pr_g2_grid": 3, "pr_g1_grid": 10}
    labels = {"pr_%s_l" % name: label.replace("[?mod1440_pr_a^num]", "26").replace("[?mod1440_of_rows^num]", "34")
              .replace("[?mod1440_pr_d^num]", "8").replace("[?mod1440_pr_h^num]", "3")
              for name, _a, _e, _x, _y, _c, _l, _w, label in PROBE_LISTS}
    checklist = [
        "Every cell: left the image = portrait icon, right the table's sprite (mod1440_p), the name under them; game.log has one 'MOD1440 probe <list> <n>: <name>' line per cell, and the window's names match those lines",
        "A (every_army_leader): each general shows his own face on the left. Road to 56 gives these generals texture files: Wilhelm Keitel, Franz Halder (r56_portrait_GER_*.dds), and the rest of the German generals as Portrait_Germany_*.dds files; a face on the left where the right shows the unknown leader or another picture is the finding. Compare three faces with the game's own general window (army view, the general's portrait)",
        "B (the Officers page's own mod1440_of_rows): the same faces as A for the same officers, the admirals among them; proves the mod's kept references work as a row scope",
        "C (an array of one): Wilhelm Keitel with his Road to 56 portrait (a texture file); the single-slot case",
        "D (every_navy_leader): each admiral his own face (Road to 56: Otto Ciliax as r56_portrait_GER_Otto_Ciliax.dds; Raeder, Donitz, Saalwachter, Lutjens, Boehm, Marschall as Portrait_Germany_*.dds); compare one with the game's fleet view",
        "E (create_corps_commander, 'Probe General'): a face from the portrait pools on the left, not the unknown leader; the right shows the unknown leader (the table cannot know him). Compare with his portrait in the game's army view, which must be the same face",
        "F (head of government, Adolf Hitler, no command): the left is EMPTY (or the unknown leader: write down which); the right shows the table's sprite. error.log: no new line naming 'portrait', 'sprite type' or the probe",
        "H (command by effect: Heinrich Himmler, Martin Bormann, Wilhelm Canaris, no number, kept by place): Himmler and Bormann their own army faces (Himmler as Road to 56's file), Canaris a pool face (he has no large army portrait), not his civilian portrait",
        "Z (control, own sprite the unknown woman): the first of A and E show faces as in A and E; F shows whatever F shows. Wherever a cell shows the woman's outline, the property did nothing there",
        "G full size (C, E, H1): the same faces at 156x210, sharp; G at 0.22 (the first ten of A): the same faces as A at the Officers list's size (34x46). Scale applies to the drawn portrait",
        "The capture 'redraw' (after effect mod1440_chk_probe_redraw): the same faces in every cell",
        "error.log: no line naming mod1440_probe, MOD1440_PR, 'portrait' or a GFX_ sprite that the window names; game.log: the 'MOD1440 probe: GER, A .. B .. ' count line and one line per row",
        "The clock still reads 1 January 1936 (no time ran); autosave.hoi4 hash unchanged",
    ]
    scene = {
        "_comment": "Written by tools/check_effects.py --probe (phase E7, throwaway), removed with --restore. Keys: wiki/Game-Recipes.md.",
        "screen": "probe_portraits",
        "phase": "E7",
        "file": "%s.gui" % PROBE_WINDOW,
        "screenshot": "reference/vanilla/theatre_bar.jpg",
        "modOnly": True,
        "windows": [{
            "at": list(PROBE_AT), "freeWindow": True, "name": PROBE_WINDOW, "rows": rows,
            "listRows": {"pr_%s_grid" % name: entry for name, _a, entry, *_ in PROBE_LISTS},
            "_note": "A portrait is the unknown leader in the renderer; in the game the left icon of each cell is the probe."}],
        "samples": {
            PROBE_WINDOW: labels,
            "mod1440_probe_cell": {"pr_name": "Gerd von Rundstedt"},
            "mod1440_probe_cell_ctl": {"pr_name": "Adolf Hitler"},
            "mod1440_probe_cell_small": {"pr_name_s": "Walther von Brauchitsch"},
            "mod1440_probe_cell_full": {"pr_name_f": "Wilhelm Keitel"},
        },
        "setup": [{"console": "effect mod1440_chk_probe", "wait": 4.0}],
        "captures": [{"name": "redraw", "steps": [{"console": "effect mod1440_chk_probe_redraw", "wait": 2.0}]}],
        "expect": ["%s/pr_close" % PROBE_WINDOW],
        "crop": [PROBE_AT[0] - 10, PROBE_AT[1] - 10, PROBE_AT[0] + PROBE_SIZE[0] + 10, PROBE_AT[1] + PROBE_SIZE[1] + 10],
        "checklist": checklist,
        "teardown": [{"console": "effect mod1440_chk_probe_close", "wait": 1.0}],
    }
    return json.dumps(scene, indent=2, ensure_ascii=False) + "\n"


def probe_contents():
    return {PROBE_FILES["gui"]: probe_gui(), PROBE_FILES["script"]: probe_script(), PROBE_FILES["loc"]: probe_loc(),
            PROBE_FILES["scene"]: probe_scene()}


HISTORY += probe_effects()
# --- end E7 probe ---

# --- E7 ---
HISTORY += ("""
# ---- E7 (2026-10-29), step 2: the game's own faces on the pages (image = "portrait", SGUI-053). As Germany on
# 1 January 1936, Road to 56 loaded.

# Himmler, Bormann and Canaris get a command by effect: unit leaders without a number, kept by their place (X66). After
# a day (or a click on a filter of the Officers page) they are rows of the Officers page with their own faces: Road to
# 56 gives Himmler's army portrait as a texture file, Canaris only his civilian large one.
mod1440_chk_e7_generals = {
%s}

# The officer chosen on the Officers page leaves the service (retire): from the next day his row (filter Former) and
# his file show the table's portrait, no longer the game's.
mod1440_chk_e7_retire = {
\tif = {
\t\tlimit = { check_variable = { mod1440_of_has_sel = 1 } }
\t\tvar:mod1440_of_sel = {
\t\t\tretire = yes
\t\t\t# not known before E7's check: does a retired leader still answer is_unit_leader = yes? (if so the pages would
\t\t\t# draw the unknown man for him: SGUI-053)
\t\t\tif = { limit = { is_unit_leader = yes } log = "MOD1440 e7 retired [This.GetName]: is_unit_leader yes" }
\t\t\telse = { log = "MOD1440 e7 retired [This.GetName]: is_unit_leader no" }
\t\t}
\t}
}

# E7 fix round 1: a state taken from Poland with a German general on the spot (check 2: with Road to 56 Danzig belongs to
# the Free City, so mod1440_chk_state2 gave 'Received from' and no general). Needs the war (mod1440_chk_war) and a
# commander for the army in Brandenburg (Army 1 with Keitel, as the Army Readiness item does). The divisions that stand
# in Brandenburg (state 64) are moved by teleport_armies to Poznan (state 86, Poland's in the game and in Road to 56),
# then Germany takes control of Poznan: the War Diary's 'State taken Poznan' names the general with the most divisions
# there, the war's file counts it for him, and Poznan's state card says 'by the troops of' him.
mod1440_chk_e7_take = {
\t64 = { teleport_armies = { to_state = 86 limit = { tag = GER } } }
\tset_temp_variable = { e7_n = 0 }
\t86 = { every_state_division = { limit = { OWNER = { tag = GER } } add_to_temp_variable = { e7_n = 1 } } }
\tset_state_controller = 86
\tlog = "MOD1440 e7 take: [?e7_n] German divisions in Poznan before Germany takes it"
}

# The same once more, if the first left no general on the line (the divisions arrived after the change of hands):
# Poland takes Poznan back and Germany takes it again, with the divisions now there.
mod1440_chk_e7_take_again = {
\tPOL = { set_state_controller = 86 }
\tset_state_controller = 86
}

# What the pages hold of the game's faces, into game.log ("MOD1440 e7"): the officer's file, the commanders of the war
# on show, the chiefs and members of the high command, the rows of the War Diary's page.
mod1440_chk_e7_log = {
\tlog = "MOD1440 e7: file [?mod1440_of_c_ul^num] [?mod1440_of_sel.GetName]; war k [?mod1440_wr_k_0_ul^num] [?mod1440_wr_k_1_ul^num] [?mod1440_wr_k_2_ul^num] [?mod1440_wr_k_3_ul^num] [?mod1440_wr_k_4_ul^num]; chiefs [?mod1440_gv_of_0_ul^num] [?mod1440_gv_of_1_ul^num] [?mod1440_gv_of_2_ul^num] [?mod1440_gv_of_3_ul^num]; members [?mod1440_gv_hc_0_ul^num] [?mod1440_gv_hc_1_ul^num] [?mod1440_gv_hc_2_ul^num]; diary rows [?mod1440_wd_fam^num] faces [?mod1440_wd_ga^num] [?mod1440_wd_gc^num]"
\tfor_each_loop = {
\t\tarray = mod1440_wd_ga
\t\tvalue = e7_v
\t\tindex = e7_i
\t\tif = {
\t\t\tlimit = { check_variable = { mod1440_wd_ua^e7_i = 1 } }
\t\t\tlog = "MOD1440 e7 diary [?e7_i]: [?e7_v.GetName], kept as [?e7_v]"
\t\t}
\t}
}
""" % "".join("\tif = { limit = { has_character = %s } add_corps_commander_role = { character = %s %s } }\n" % (c, c, SKILLS)
              for c in PROBE_BY_EFFECT))
# --- end E7 ---


def throwaway_files():
    """Every file this tool writes: the check effects and the probe's files."""
    return [PATH] + [os.path.join(ROOT, rel) for rel in PROBE_FILES.values()]


if __name__ == "__main__":
    if "--check" in sys.argv:
        present = [p for p in throwaway_files() if os.path.isfile(p)]
        for p in present:
            print("present (remove with python -I tools/check_effects.py --restore):", os.path.relpath(p, ROOT))
        sys.exit(1 if present else 0)
    if "--restore" in sys.argv:
        for p in throwaway_files():
            if os.path.isfile(p):
                os.remove(p)
                print("removed", p)
    else:
        io.open(PATH, "w", encoding="utf-8", newline="\n").write(EFFECTS + HISTORY)
        print("wrote", PATH)
        if "--probe" in sys.argv:
            for rel, content in probe_contents().items():
                path = os.path.join(ROOT, rel)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                io.open(path, "w", encoding="utf-8", newline="\n").write(content)
                print("wrote", rel)
        # a running game reads the script again when a file under common/scripted_guis has a new time stamp
        folder = os.path.join(ROOT, "common", "scripted_guis")
        now = time.time()
        for name in os.listdir(folder):
            os.utime(os.path.join(folder, name), (now, now))
