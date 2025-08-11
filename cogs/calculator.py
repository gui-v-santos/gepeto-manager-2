"""
Módulo para cálculos complexos de crafting e custos.
"""

def find_price(item_name, precos_data):
    """
    Procura o preço de um item em todas as categorias de preços.
    Retorna uma tupla (min_price, max_price) ou (None, None) se não encontrado.
    """
    for categoria in precos_data.values():
        if isinstance(categoria, dict):
            # Procura em 'min' e 'range' para abranger ambas as estruturas
            if 'min' in categoria and isinstance(categoria.get('min'), dict) and item_name in categoria['min']:
                return categoria['min'][item_name], categoria['min'][item_name]
            if 'range' in categoria and isinstance(categoria.get('range'), dict) and item_name in categoria['range']:
                price_info = categoria['range'][item_name]
                return price_info.get('min'), price_info.get('max')
    return None, None

def calcular_custo_craft(item_nome, quantidade, receitas, precos, memo=None):
    """
    Calcula o custo de craft de um item de forma recursiva, com memoization.
    Retorna o custo mínimo e máximo total para a quantidade desejada.
    """
    if memo is None:
        memo = {}

    def get_custo_unitario(item):
        """
        Função auxiliar recursiva que calcula o custo unitário de um item.
        Usa o cache 'memo' para evitar recalcular custos.
        """
        if item in memo:
            return memo[item]

        # 1. Tenta encontrar um preço de compra direto (matéria-prima)
        preco_min_direto, preco_max_direto = find_price(item, precos)
        if preco_min_direto is not None:
            # Se encontrou um preço, usa como custo base.
            custo_max = preco_max_direto if preco_max_direto is not None else preco_min_direto
            memo[item] = (preco_min_direto, custo_max)
            return preco_min_direto, custo_max

        # 2. Se não tem preço direto, verifica se tem receita para craft
        if item not in receitas:
            # Não tem preço e não tem receita, custo é 0.
            # (Ex: Madeira Bruta, Carvão - o usuário precisa adicionar preços para esses)
            memo[item] = (0, 0)
            return 0, 0

        # 3. Calcula o custo com base nos materiais da receita
        receita = receitas[item]
        custo_total_materiais_min = 0
        custo_total_materiais_max = 0

        for material in receita['materiais']:
            nome_material = material['nome']
            qtd_material = material['quantidade']

            # Custo unitário do material (recursivo)
            custo_unit_material_min, custo_unit_material_max = get_custo_unitario(nome_material)

            custo_total_materiais_min += custo_unit_material_min * qtd_material
            custo_total_materiais_max += custo_unit_material_max * qtd_material

        # Divide o custo total pela quantidade que a receita produz
        produz = receita.get('produz', 1)
        custo_unitario_min = custo_total_materiais_min / produz
        custo_unitario_max = custo_total_materiais_max / produz

        memo[item] = (custo_unitario_min, custo_unitario_max)
        return custo_unitario_min, custo_unitario_max

    # Calcula o custo unitário do item final solicitado
    custo_unit_min, custo_unit_max = get_custo_unitario(item_nome)

    # Multiplica pela quantidade desejada
    total_min = round(custo_unit_min * quantidade, 2)
    total_max = round(custo_unit_max * quantidade, 2)

    return total_min, total_max
