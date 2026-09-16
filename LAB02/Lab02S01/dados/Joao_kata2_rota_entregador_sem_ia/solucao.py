def posicao_final(comandos: list[str], tamanho_grade: int) -> dict:
    x = 0
    y = 0
    saiu_da_grade = False 
    
    for comando in comandos:
        direcao = comando[0]
        if direcao not in ['N', 'S', 'L', 'O']:
            raise ValueError("Direcao invalida")
            
        passos = int(comando[1:])

        for _ in range(passos):
            novo_x = x
            novo_y = y
            
            if direcao == 'N':
                novo_y += 1
            elif direcao == 'S':
                novo_y -= 1
            elif direcao == 'L':
                novo_x += 1
            elif direcao == 'O':
                novo_x -= 1
            
            if 0 <= novo_x < tamanho_grade and 0 <= novo_y <= tamanho_grade:
                x = novo_x
                y = novo_y
            else:
                saiu_da_grade = True

    return {"x": x, "y": y, "saiu_da_grade": saiu_da_grade}