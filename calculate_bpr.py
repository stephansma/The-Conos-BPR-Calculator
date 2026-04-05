import json
import requests
import pulp # The mathematical optimization library

LEAGUE_ID = "gqckve2rmaw4e4ls"
FANTRAX_ROSTER_URL = f"https://www.fantrax.com/fxea/general/getTeamRosters?leagueId={LEAGUE_ID}"

def get_player_stats():
    # In a full build, this function will cross-reference the NHL API
    # to grab total G, A, W, and SO for the current season.
    # For now, this returns the data structure we need.
    pass 

def optimize_team_roster(team_name, roster):
    """
    Finds the Best Possible Roster mathematically.
    Roster is a list of dictionaries: [{'name': 'McDavid', 'positions': ['C'], 'points': 120}, ...]
    """
    # Create the linear programming problem
    prob = pulp.LpProblem(f"Optimize_{team_name}", pulp.LpMaximize)
    
    # Create variables for every player at every position they are eligible for
    # e.g., A variable for J.T. Miller as a C, and J.T. Miller as a RW
    player_vars = {}
    for i, player in enumerate(roster):
        for pos in player['positions']:
            var_name = f"player_{i}_{pos}"
            player_vars[(i, pos)] = pulp.LpVariable(var_name, cat='Binary')
            
    # Objective: Maximize total points
    prob += pulp.lpSum([roster[i]['points'] * var for (i, pos), var in player_vars.items()])
    
    # Constraint 1: A player can only be used ONCE (or zero times)
    for i in range(len(roster)):
        prob += pulp.lpSum([player_vars[(i, pos)] for pos in roster[i]['positions'] if (i, pos) in player_vars]) <= 1
        
    # Constraint 2: Exactly 16 starting spots filled correctly
    prob += pulp.lpSum([var for (i, pos), var in player_vars.items() if pos == 'LW']) == 3
    prob += pulp.lpSum([var for (i, pos), var in player_vars.items() if pos == 'RW']) == 3
    prob += pulp.lpSum([var for (i, pos), var in player_vars.items() if pos == 'C']) == 3
    prob += pulp.lpSum([var for (i, pos), var in player_vars.items() if pos == 'D']) == 4
    prob += pulp.lpSum([var for (i, pos), var in player_vars.items() if pos == 'G']) == 3
    
    # Solve the optimization problem
    prob.solve()
    
    # Extract the winning optimal roster
    optimal_roster = []
    total_score = pulp.value(prob.objective)
    
    for (i, pos), var in player_vars.items():
        if var.varValue == 1.0:
            optimal_roster.append({
                "name": roster[i]['name'],
                "locked_position": pos,
                "points": roster[i]['points']
            })
            
    return {"bpr_score": total_score, "optimal_roster": optimal_roster}

def main():
    # 1. Fetch data from Fantrax
    # 2. Fetch stats from NHL
    # 3. Combine them
    # 4. Loop through every team and run optimize_team_roster()
    # 5. Save everything to a clean data.json file
    
    # Placeholder for the final JSON write
    dummy_data = {"standings": [], "last_updated": "2024-10-25"}
    with open("data.json", "w") as outfile:
        json.dump(dummy_data, outfile)

if __name__ == "__main__":
    main()
