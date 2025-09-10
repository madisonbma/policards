# policards

Flow (done in main.py):
    1. gen_reps_json (if selected): will run API pull from congress.gov to get congressmember info
    2. gen_voting_record_json (if selected): will run API pull from congress.gov to get record of votes
    3. Takes the outputs of both of these [JSON] and modifies/data crunches
        modify_reps:
            merges with bonus data from bioguide.congress.gov (add_bioguide.py)
            crunches voting data (modify_votes.py) and adds it in
    4. gen_cards will take the data from reps and generate player cards
