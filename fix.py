with open('backend/repositories/database_repo.py', 'r') as f:
    lines = f.readlines()

new_lines = []
in_bad_block = False
for i, line in enumerate(lines):
    if line.strip() == '"farmer_name": r.farmer_name,' and i+1 < len(lines) and lines[i+1].strip() == 'row = res.scalars().first()':
        in_bad_block = True
        new_lines.append(line)
        new_lines.append('                "status": r.status,\n')
        new_lines.append('                "current_round": r.current_round,\n')
        new_lines.append('                "summary": r.summary,\n')
        new_lines.append('                "final_price": r.final_price,\n')
        new_lines.append('                "market_price": r.market_price,\n')
        new_lines.append('                "min_price": r.min_price,\n')
        new_lines.append('                "transport_plan": r.transport_plan,\n')
        new_lines.append('                "peer_node": r.peer_node,\n')
        new_lines.append('                "logs": r.logs or [],\n')
        new_lines.append('                "market_offers": r.market_offers or [],\n')
        new_lines.append('                "selected_buyer": r.selected_buyer or {},\n')
        new_lines.append('                "signatures": r.signatures or {},\n')
        new_lines.append('            })\n')
        new_lines.append('        # Sync in-memory cache\n')
        new_lines.append('        for neg in results:\n')
        new_lines.append('            Database.negotiations[neg["negotiation_id"]] = neg\n')
        new_lines.append('        return results\n')
        continue
        
    if in_bad_block:
        if line.strip() == '@classmethod' and i+1 < len(lines) and lines[i+1].strip().startswith('def get_market_mappings'):
            in_bad_block = False
            new_lines.append(line)
        continue
        
    new_lines.append(line)

with open('backend/repositories/database_repo.py', 'w') as f:
    f.writelines(new_lines)
