# policards

Flow (done in src/main.py):
    1. gen_reps_json (if selected): will run API pull from congress.gov to get congressmember info
        Outputs: generated_outputs/congressmen.json
    2. gen_voting_record_json (if selected): will run API pull from congress.gov to get record of house votes, from senate.gov for senate. No longer regenerates, will instead load votes in and pull any votes that haven't already been pulled, and append.
        Outputs: voting_records.json
                 voting_records_senate.json
    3. Takes the outputs of both of these [JSON] and modifies/data crunches
        modify_votes: 
            takes in house and senate voting records, merges and gets aggregate voting records for the year.
                Outputs: vote_avg.json
        modify_reps:
            merges with bonus data from bioguide.congress.gov (add_bioguide.py)
            crunches voting data (modify_votes.py) and adds it in
    4. gen_cards will take the data from reps and generate player cards
