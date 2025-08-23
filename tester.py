import gen_reps_json
import gen_voting_record_json
import modify_reps
import modify_votes
import gen_xls
import gen_cards
import sys
import os
import time


if __name__ == "__main__":
    #Generate the representative json if it doesn't exist or if forcing override.

    #gen_reps_json.gen_reps_json()

    #gen_voting_record_json.gen_voting_record_json()    
    #modify_votes.modify_votes("voting_records.json")
    modify_reps.modify_reps("congressmen.json", "vote_avg.json")

    #gen_cards.gen_cards('congressmen_mod.json', test_card=True)
        