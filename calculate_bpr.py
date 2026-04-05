import json
import requests
import pulp 
import unicodedata

LEAGUE_ID = "gqckve2rmaw4e4ls"

def normalize_name(name):
    """Removes special characters, accents, and punctuation to match names between APIs."""
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('utf-8')
    return name.lower().replace(".", "").replace("'", "").replace("-", " ").strip()

def get_nhl_stats():
    """Fetches real-time stats from the NHL API and calculates our specific fantasy points."""
    print("Fetching NHL Stats...")
    stats_map = {}
    
    # Fetch Skaters (Using the NHL REST API for the 2024-2025 season)
    skater_url = "https://api.nhle.com/stats/rest/en/skater/summary?limit=1500&cayenneExp=seasonId=20242025%20and%20gameTypeId=2"
    skater_data = requests.get(skater_url).json().get('data', [])
    
    for s in skater_data:
        name = normalize_name(s['skaterFullName'])
        # Skaters: 1 pt for each Point (Goals + Assists)
        stats_map[name] = s['points']
        
    # Fetch Goalies
    goalie_url = "https://api.nhle.com/stats/rest/en/goalie/summary?limit=150&cayenneExp=seasonId=20242025%20and%20gameTypeId=2"
    goalie_data = requests.get(goalie_url).json().get('data', [])
    
    for g in goalie_data:
        name = normalize_name(g['skaterFullName'])
        # Goalies: 2 pts for a Win, 2 pts for a Shutout
        stats_map[name] = (g['wins'] * 2) + (g['shutouts'] * 2)
        
    return stats_map

def optimize_team_roster(team_name, roster):
    """Finds the Best Possible Roster mathematically."""
    prob = pulp.LpProblem(f"Optimize_{team_name.replace(' ', '_')}", pulp.LpMaximize)
    
    player_vars = {}
    for i, player in enumerate(roster):
        for pos in player['positions']:
            var_name = f"player_{i}_{pos}"
            player_vars[(i, pos)] = pulp.LpVariable(var_name, cat='Binary')
            
    # Objective: Maximize points
    prob += pulp.lpSum([roster[i]['points'] * var for (i, pos), var in player_vars.items()])
    
    # A player can only be used ONCE
    for i in range(len(roster)):
        prob += pulp.lpSum([player_vars[(i, pos)] for pos in roster[i]['positions'] if (i, pos) in player_vars]) <= 1
        
    # Roster Limits
    prob += pulp.lpSum([var for (i, pos), var in player_vars.items() if pos == 'LW']) == 3
    prob += pulp.lpSum([var for (i, pos), var in player_vars.items() if pos == 'RW']) == 3
    prob += pulp.lpSum([var for (i, pos), var in player_vars.items() if pos == 'C']) == 3
    prob += pulp.lpSum([var for (i, pos), var in player_vars.items() if pos == 'D']) == 4
    prob += pulp.lpSum([var for (i, pos), var in player_vars.items() if pos == 'G']) == 3
    
    prob.solve(pulp.PULP_CBC_CMD(msg=0)) # msg=0 hides the math logs
    
    optimal_roster = []
    total_score = pulp.value(prob.objective)
    
    for (i, pos), var in player_vars.items():
        if var.varValue == 1.0:
            optimal_roster.append({
                "name": roster[i]['name'],
                "locked_position": pos,
                "points": roster[i]['points']
            })
            
    # Sort roster so it looks clean on the UI
    position_order = {"C": 1, "LW": 2, "RW": 3, "D": 4, "G": 5}
    optimal_roster.sort(key=lambda x: (position_order.get(x["locked_position"], 99), -x["points"]))
            
    return {"bpr_score": int(total_score) if total_score else 0, "optimal_roster": optimal_roster}

def main():
    # 1. Fetch NHL Stats
    nhl_stats = get_nhl_stats()
    
    # 2. Fetch Fantrax Player Dictionary
    print("Fetching Fantrax Player Dictionary...")
    players_url = "https://www.fantrax.com/fxea/general/getPlayerIds?sport=NHL"
    fantrax_players = requests.get(players_url).json()
    
    # 3. Fetch Team Rosters
    print("Fetching League Rosters...")
    roster_url = f"https://www.fantrax.com/fxea/general/getTeamRosters?leagueId={LEAGUE_ID}"
    rosters_data = requests.get(roster_url).json()
    
    final_standings = []
    
    # 4. Map everything together
    for team_id, team_data in rosters_data.items():
        team_name = team_data.get('teamName', f"Team {team_id}")
        team_roster_payload = []
        
        for player_item in team_data.get('rosterItems', []):
            fantrax_id = player_item.get('id')
            
            # Lookup player info in the master dictionary
            player_info = fantrax_players.get(fantrax_id)
            if not player_info:
                continue
                
            raw_name = player_info.get('name')
            positions_str = player_info.get('positions', '')
            positions_list = [p.strip() for p in positions_str.split(',') if p.strip()]
            
            # Match with NHL stats
            normalized_name = normalize_name(raw_name)
            points = nhl_stats.get(normalized_name, 0)
            
            team_roster_payload.append({
                "name": raw_name,
                "positions": positions_list,
                "points": points
            })
            
        # 5. Run the Optimizer
        print(f"Optimizing {team_name}...")
        optimization_result = optimize_team_roster(team_name, team_roster_payload)
        
        final_standings.append({
            "team_name": team_name,
            "bpr_score": optimization_result["bpr_score"],
            "roster": optimization_result["optimal_roster"]
        })
        
    # Sort standings highest to lowest
    final_standings.sort(key=lambda x: x["bpr_score"], reverse=True)
    
    # Save the output for the website to read
    output_data = {"standings": final_standings}
    with open("data.json", "w") as outfile:
        json.dump(output_data, outfile, indent=4)
    print("Optimization Complete! Saved to data.json")

if __name__ == "__main__":
    main()