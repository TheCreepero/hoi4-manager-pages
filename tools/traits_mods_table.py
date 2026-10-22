"""Made by tools/make_game_tables.py --mods from the mods of the launcher's playset: run it again when the
playset changes. Delete this file for a build that knows the game's own traits only.

TRAITS: the traits of unit leaders the playset has and the game lacks, rows as in traits_table.py.
GONE: the game's traits the playset does not define.
46 traits, 1 gone."""

MODS = ['RT56 - VNR - UTT Standalone v14']

TRAITS = [
    ('jaeger_trait', 'army', 'GFX_trait_jaeger_trait'),
    ('submarine_captain', 'navy', 'GFX_trait_submarine_captain'),
    ('lucky', 'army', 'GFX_trait_lucky'),
    ('vigorous', 'army', 'GFX_trait_vigorous'),
    ('promising', 'both', 'GFX_trait_promising'),
    ('air_force_ties', 'army', 'GFX_trait_air_force_ties'),
    ('artillerist', 'army', 'GFX_trait_artillerist'),
    ('caring_leader', 'army', 'GFX_trait_caring_leader'),
    ('obsessed_by_artillery', 'army', 'GFX_trait_obsessed_by_artillery'),
    ('meticulous', 'army', 'GFX_trait_meticulous'),
    ('decided_planner', 'army', 'GFX_trait_decided_planner'),
    ('homeland_connoisseur', 'army', 'GFX_trait_homeland_connoisseur'),
    ('unpopular', 'army', 'GFX_trait_unpopular'),
    ('funnies_inventor', 'army', 'GFX_trait_funnies_inventor'),
    ('bad_staffer', 'army', 'GFX_trait_bad_staffer'),
    ('flemish', 'both', 'GFX_trait_flemish'),
    ('walloon', 'both', 'GFX_trait_walloon'),
    ('retraining', 'army', 'GFX_trait_retraining'),
    ('jumping_general', 'army', 'GFX_trait_jumping_general'),
    ('skeletons_blessing', 'army', 'GFX_trait_skeletons_blessing'),
    ('attentive_surgeon', 'army', 'GFX_trait_attentive_surgeon'),
    ('EGY_aristocrat', 'both', 'GFX_trait_EGY_aristocrat'),
    ('EGY_brotherhood_sympathiser', 'both', ''),
    ('AFG_barakzai_royalist', 'both', 'GFX_trait_AFG_barakzai_royalist'),
    ('AUS_nazi_loyalties', 'both', 'GFX_trait_AUS_nazi_loyalties'),
    ('ARM_anti_communist_sympathizer', 'both', 'GFX_trait_ARM_anti_communist_sympathizer'),
    ('MEN_fascist_sympathies', 'both', 'GFX_trait_MEN_fascist_sympathies'),
    ('too_young_too_simple', 'army', ''),
    ('sometimes_naive', 'army', ''),
    ('i_am_angry', 'army', ''),
    ('black_rimmed_glasses', 'army', ''),
    ('experienced_100_battles', 'army', ''),
    ('r56w_trait_generic_is_breathing', 'both', ''),
    ('r56w_trait_marshal_master_exploder', 'both', 'GFX_trait_r56w_trait_marshal_master_exploder'),
    ('r56w_trait_army_vibrates', 'both', 'GFX_trait_r56w_trait_army_vibrates'),
    ('r56w_trait_army_packed_lunch', 'both', 'GFX_trait_r56w_trait_army_packed_lunch'),
    ('r56w_trait_army_saw_a_squirrel', 'both', 'GFX_trait_r56w_trait_army_saw_a_squirrel'),
    ('r56w_trait_army_knows_what_you_did', 'both', 'GFX_trait_r56w_trait_army_knows_what_you_did'),
    ('r56w_trait_army_force_user', 'both', 'GFX_trait_r56w_trait_army_force_user'),
    ('r56w_trait_army_is_a_lemur', 'both', 'GFX_trait_r56w_trait_army_is_a_lemur'),
    ('r56w_trait_army_personal_space', 'both', 'GFX_trait_r56w_trait_army_personal_space'),
    ('r56w_trait_army_free_coffee', 'both', 'GFX_trait_r56w_trait_army_free_coffee'),
    ('r56w_trait_navy_ocean_haiku', 'both', 'GFX_trait_r56w_trait_navy_ocean_haiku'),
    ('r56w_trait_navy_hates_water', 'both', 'GFX_trait_r56w_trait_navy_hates_water'),
    ('r56w_trait_navy_rubber_duck', 'both', 'GFX_trait_r56w_trait_navy_rubber_duck'),
    ('r56w_trait_navy_can_swim', 'both', 'GFX_trait_r56w_trait_navy_can_swim'),
]

GONE = ['jaeger']
