#!/usr/bin/env python3
"""
Script para corregir los tests que crean ChatTurn sin el campo openrouter_risk_accepted.
Se ejecuta en la VM vía SSH.
"""
import subprocess
import sys

REMOTE_COMMAND = r'''
set -e
cd /opt/superharry/app

# Archivos a corregir
FILES="home/test_chat.py home/test_chat_provider_routing.py home/test_chat_cancellation.py home/test_chat_reattachment.py home/test_gemini_chat.py home/test_gemini_queue.py home/test_message_history.py home/test_t179_integration.py"

for f in $FILES; do
    if [ ! -f "$f" ]; then
        echo "SKIP (no existe): $f"
        continue
    fi
    
    echo "=== Procesando: $f ==="
    
    # Lee el archivo
    content=$(cat "$f")
    
    # Patron: ChatTurn.objects.create( seguido de parametros
    # Necesitamos agregar openrouter_risk_accepted=False antes del cierre del dict
    # Enfoque: usar python para hacer la corrección
    python3 << 'PYEOF'
import re
import sys

with open(sys.argv[1], 'r') as f:
    content = f.read()

# Buscar patrones de ChatTurn.objects.create(
# y agregar openrouter_risk_accepted=False antes del cierre del ultimo parentesis
# El patron es: ChatTurn.objects.create( ... ) 
# donde ... incluye varios parametros

# Usamos un enfoque mas robusto: encontrar la linea que empieza con ChatTurn.objects.create(
# y la bloque completo

lines = content.split('\n')
output = []
in_create = False
create_line_idx = -1
open_parens = 0

for i, line in enumerate(lines):
    stripped = line.strip()
    
    if stripped.startswith('ChatTurn.objects.create('):
        in_create = True
        create_line_idx = i
        open_parens = line.count('(') - line.count(')')
        output.append(line)
        continue
    
    if in_create:
        # Cuenta parentesis de apertura/cierre en esta linea
        new_open = line.count('(') - line.count(')')
        open_parens += new_open
        
        if open_parens <= 0:
            # Esta linea cierra el create
            # Verificar si ya tiene openrouter_risk_accepted
            if 'openrouter_risk_accepted' not in line:
                # Verificar si es un multilinea con parentesis al final
                # Agregar el campo antes del último parentesis
                if line.rstrip().endswith(')'):
                    # Quitar el ultimo )
                    line = line.rstrip()[:-1]
                    # Agregar el campo antes del cierre
                    indent = line[:len(line) - len(line.lstrip())]
                    line = line.rstrip() + ',\n' + indent + '            openrouter_risk_accepted=False'
                output.append(line)
            else:
                output.append(line)
            in_create = False
            continue
        
        output.append(line)
        continue
    
    # No esta en un create
    output.append(line)

with open(sys.argv[1], 'w') as f:
    f.write('\n'.join(output))

print("  Done")
