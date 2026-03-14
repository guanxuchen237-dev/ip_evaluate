import os

filepath = 'd:/ip-lumina-main/integrated_system/backend/api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_route = '''@api_bp.route('/charts/long_term_trend')
def chart_long_term_trend():
    platform = request.args.get('platform', 'qidian')
    data = data_manager.get_long_term_trend(platform=platform)
    return jsonify(data)

@api_bp.route('/library/list')'''

if 'def chart_long_term_trend' not in content:
    content = content.replace("@api_bp.route('/library/list')", new_route)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
        print("Updated api.py")
else:
    print("Already updated api.py")
