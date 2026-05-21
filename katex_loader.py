"""
katex_loader.py: Module pour charger KaTeX en mode inline (embedded base64)
À placer dans le même dossier que main_window.py
"""

import os
import base64
import re


# katex_loader.py
def load_katex_inline():
    """
    Charge tous les fichiers KaTeX et les convertit en base64 pour 
    les embarquer directement dans le HTML.
    
    Returns:
        tuple: (css_content, katex_js, autorender_js)
    """
    # Trouver le dossier katex
    script_dir = os.path.dirname(os.path.abspath(__file__))
    katex_dir = os.path.join(script_dir, 'katex')
    
    if not os.path.exists(katex_dir):
        raise FileNotFoundError(f"Dossier KaTeX introuvable: {katex_dir}")
    
    #print(f"📂 Chargement KaTeX depuis: {katex_dir}")
    
    try:
        # 1. Lire le CSS
        css_path = os.path.join(katex_dir, 'katex.min.css')
        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
        #print(f"  ✅ CSS chargé ({len(css_content):,} chars)")
        
        # 2. Lire katex.min.js
        katex_js_path = os.path.join(katex_dir, 'katex.min.js')
        with open(katex_js_path, 'r', encoding='utf-8') as f:
            katex_js = f.read()
        #print(f"  ✅ katex.min.js chargé ({len(katex_js):,} chars)")
        
        # 3. Lire auto-render.min.js
        autorender_path = os.path.join(katex_dir, 'contrib', 'auto-render.min.js')
        with open(autorender_path, 'r', encoding='utf-8') as f:
            autorender_js = f.read()
        #print(f"  ✅ auto-render.min.js chargé ({len(autorender_js):,} chars)")
        
        # 4. Convertir toutes les fonts en base64
        fonts_dir = os.path.join(katex_dir, 'fonts')
        if os.path.exists(fonts_dir):
            #print("  🔄 Conversion des fonts en base64...")
            font_count = 0
            for font_file in os.listdir(fonts_dir):
                if font_file.endswith('.woff2'):
                    font_path = os.path.join(fonts_dir, font_file)
                    with open(font_path, 'rb') as f:
                        font_data = base64.b64encode(f.read()).decode()
                    
                    # Remplacer dans le CSS
                    old_url = f'url(fonts/{font_file})'
                    new_url = f'url(data:font/woff2;base64,{font_data})'
                    css_content = css_content.replace(old_url, new_url)
                    font_count += 1
            
            #print(f"  ✅ {font_count} fonts converties")
        
        #print("✅ KaTeX chargé avec succès!\n")
        return css_content, katex_js, autorender_js
        
    except FileNotFoundError as e:
        print(f"❌ Fichier manquant: {e}")
        raise
    except Exception as e:
        print(f"❌ Erreur lors du chargement: {e}")
        raise


def clean_latex_for_copy(text):
    """
    Nettoie le texte LaTeX pour la copie:
    - Supprime \\begin{solution}...\\end{solution} wrappers
    - Supprime \\begin{exercise}...\\end{exercise} wrappers
    - Garde tout le contenu LaTeX interne
    
    Args:
        text: Texte LaTeX brut
    
    Returns:
        str: Texte nettoyé pour copie
    """
    if not text:
        return ""
    
    cleaned = text.strip()
    
    # Remove solution wrapper but keep content
    solution_match = re.search(
        r'\\begin\{solution\}(.*?)\\end\{solution\}',
        cleaned,
        re.DOTALL | re.IGNORECASE
    )
    if solution_match:
        cleaned = solution_match.group(1).strip()
    
    # Remove exercise wrapper but keep content
    exercise_match = re.search(
        r'\\begin\{exercise\}(.*?)\\end\{exercise\}',
        cleaned,
        re.DOTALL | re.IGNORECASE
    )
    if exercise_match:
        cleaned = exercise_match.group(1).strip()
    
    return cleaned


def build_chat_html_with_katex(chat_history):
    """
    Construit le HTML du chat avec KaTeX embarqué et boutons de copie.
    
    Args:
        chat_history: Liste de dicts avec 'sender', 'message', 'timestamp'
    
    Returns:
        str: HTML complet avec KaTeX inline
    """
    # Charger KaTeX
    css_content, katex_js, autorender_js = load_katex_inline()
    
    # Construire les messages
    messages_html = ""
    for idx, msg in enumerate(chat_history):
        sender = msg.get('sender', 'Unknown')
        message = msg.get('message', '')
        timestamp = msg.get('timestamp', '')
        
        if sender == "You":
            bubble_class = "user-message"
            sender_color = "#0078d4"
            copy_button = ""  # Pas de bouton pour les messages utilisateur
            text_direction = "ltr"  # User messages always LTR
        elif sender == "AI":
            bubble_class = "ai-message"
            sender_color = "#28a745"
            
            # Détecter si le message est en arabe pour définir la direction
            if contains_arabic(message):
                text_direction = "rtl"
                text_align = "right"
            else:
                text_direction = "ltr"
                text_align = "left"
            
            # Nettoyer le message pour la copie
            clean_message = clean_latex_for_copy(message)
            
            # Échapper pour JavaScript (gérer quotes, backslashes, newlines)
            escaped_message = (clean_message
                .replace('\\', '\\\\')
                .replace('`', '\\`')
                .replace('$', '\\$')
                .replace('{', '\\{')
                .replace('}', '\\}'))
            
            # Bouton de copie pour les messages AI
            copy_button = f'''
                <button class="copy-btn" onclick="copyMessage_{idx}()" title="Copy LaTeX content (without wrappers)">
                    📋 Copy
                </button>
            '''
        else:
            bubble_class = "system-message"
            sender_color = "#6c757d"
            copy_button = ""  # Pas de bouton pour les messages système
            text_direction = "ltr"  # System messages always LTR
        
        messages_html += f"""
        <div class="message {bubble_class}" dir="{text_direction}" style="text-align: {text_align if sender == 'AI' else 'left'};">
            <div class="message-header">
                <span class="sender" style="color: {sender_color};">{sender}</span>
                {copy_button}
                <span class="timestamp">{timestamp}</span>
            </div>
            <div class="message-content" id="msg-content-{idx}">
                {message}
            </div>
        </div>
        """
    
    # HTML complet
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
/* KaTeX CSS embarqué */
{css_content}

/* Styles du chat */
body {{
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    margin: 0;
    padding: 20px;
    background-color: #f5f5f5;
    font-size: 20px;
    line-height: 1.6;
}}

.message {{
    margin-bottom: 20px;
    padding: 15px;
    border-radius: 10px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    animation: fadeIn 0.3s;
}}

@keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(10px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}

.user-message {{
    background-color: #e3f2fd;
    border-left: 4px solid #0078d4;
}}

.ai-message {{
    background-color: #f1f8f4;
    border-left: 4px solid #28a745;
}}

.system-message {{
    background-color: #fff3cd;
    border-left: 4px solid #ffc107;
}}

.message-header {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(0,0,0,0.1);
}}

/* RTL support for AI messages in Arabic */
.message[dir="rtl"] .message-header {{
    flex-direction: row-reverse;
}}

.message[dir="rtl"] .timestamp {{
    margin-left: 0;
    margin-right: auto;
}}

.sender {{
    font-weight: bold;
    font-size: 16px;
    margin-right: 15px;
}}

.message[dir="rtl"] .sender {{
    margin-right: 0;
    margin-left: 15px;
}}

.timestamp {{
    color: #666;
    font-size: 14px;
    margin-left: auto;
}}

.copy-btn {{
    background-color: #007bff;
    color: white;
    border: none;
    border-radius: 5px;
    padding: 5px 12px;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
    font-weight: 600;
    margin-right: 10px;
}}

.message[dir="rtl"] .copy-btn {{
    margin-right: 0;
    margin-left: 10px;
}}

.copy-btn:hover {{
    background-color: #0056b3;
    transform: scale(1.05);
}}

.copy-btn:active {{
    transform: scale(0.95);
}}

.copy-btn.copied {{
    background-color: #28a745;
}}

.message-content {{
    color: #333;
    font-size: 18px;
    word-wrap: break-word;
    white-space: pre-wrap;
}}

/* RTL specific styles for Arabic content */
.message[dir="rtl"] .message-content {{
    text-align: right;
    direction: rtl;
    unicode-bidi: plaintext; /* Important for mixed LTR/RTL content */
}}

/* CRITICAL: Keep math equations in LTR mode even in RTL context */

/* Inline math: LTR direction but keep natural flow */
.katex {{
    direction: ltr !important;
    unicode-bidi: embed;
    display: inline-block;
}}

/* Display math: CENTERED but LTR direction */
.katex-display {{
    direction: ltr !important;
    text-align: center !important; /* Keep display math centered */
    unicode-bidi: embed;
    margin: 15px 0 !important;
}}

/* Ensure all KaTeX elements maintain LTR direction */
.katex-html,
.katex-mathml,
.katex-math,
[class*="katex"] {{
    direction: ltr !important;
}}

/* Fix for math delimiters in RTL context */
.message[dir="rtl"] .katex .base {{
    direction: ltr;
    unicode-bidi: embed;
}}

.message[dir="rtl"] .katex .mord {{
    direction: ltr;
}}

/* Ensure display math stays centered in RTL containers */
.message[dir="rtl"] .katex-display {{
    text-align: center !important;
    margin-left: auto !important;
    margin-right: auto !important;
}}

.katex {{
    font-size: 1.0em;
}}

.katex-display {{
    margin: 15px 0;
    overflow-x: auto;
    overflow-y: hidden;
}}

.katex .mtable {{
    padding: 5px 0;
}}

code {{
    background-color: #f5f5f5;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'Courier New', monospace;
    font-size: 1.0em;
}}

pre {{
    background-color: #2d2d2d;
    color: #f8f8f2;
    padding: 15px;
    border-radius: 5px;
    overflow-x: auto;
}}

::-webkit-scrollbar {{
    width: 10px;
}}

::-webkit-scrollbar-track {{
    background: #f1f1f1;
}}

::-webkit-scrollbar-thumb {{
    background: #888;
    border-radius: 5px;
}}

::-webkit-scrollbar-thumb:hover {{
    background: #555;
}}
</style>
</head>
<body>
{messages_html}

<script>
/* KaTeX JS embarqué */
{katex_js}
</script>

<script>
/* Auto-render JS embarqué */
{autorender_js}
</script>

<script>
/* Script de rendu */
console.log('=== KaTeX Inline Loading ===');
console.log('typeof katex:', typeof katex);
console.log('typeof renderMathInElement:', typeof renderMathInElement);

function renderMath() {{
    if (typeof renderMathInElement !== 'undefined') {{
        console.log('✅ Début du rendu KaTeX...');
        try {{
            renderMathInElement(document.body, {{
                delimiters: [
                    {{left: "$$", right: "$$", display: true}},
                    {{left: "\\\\[", right: "\\\\]", display: true}},
                    {{left: "$", right: "$", display: false}},
                    {{left: "\\\\(", right: "\\\\)", display: false}}
                ],
                throwOnError: false,
                errorColor: '#cc0000',
                strict: false
            }});
            
            // Force proper direction for all math elements after rendering
            document.querySelectorAll('.katex').forEach(el => {{
                el.style.direction = 'ltr';
                el.style.unicodeBidi = 'embed';
            }});
            
            // Display math should be centered but LTR
            document.querySelectorAll('.katex-display').forEach(el => {{
                el.style.direction = 'ltr';
                el.style.textAlign = 'center';
                el.style.unicodeBidi = 'embed';
                el.style.marginLeft = 'auto';
                el.style.marginRight = 'auto';
            }});
            
            console.log('✅ Rendu KaTeX terminé!');
        }} catch(e) {{
            console.error('❌ Erreur rendu KaTeX:', e);
        }}
    }} else {{
        console.error('❌ renderMathInElement non disponible');
    }}
}}

// Fonction pour détecter l'arabe
function containsArabic(text) {{
    // Plage Unicode pour les caractères arabes
    var arabicRegex = /[\u0600-\u06FF]/;
    return arabicRegex.test(text);
}}

// Fonctions de copie pour chaque message AI
"""
    
    # Générer les fonctions de copie pour chaque message AI
    for idx, msg in enumerate(chat_history):
        if msg.get('sender') == 'AI':
            clean_message = clean_latex_for_copy(msg.get('message', ''))
            # Échapper pour JavaScript template literal
            escaped = clean_message.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')
            
            html += f"""
function copyMessage_{idx}() {{
    const text = `{escaped}`;
    
    // Utiliser l'API Clipboard moderne
    if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(text).then(function() {{
            const btn = event.target;
            const originalText = btn.textContent;
            btn.textContent = '✅ Copied!';
            btn.classList.add('copied');
            
            setTimeout(function() {{
                btn.textContent = originalText;
                btn.classList.remove('copied');
                btn.style.backgroundColor = '#007bff';
            }}, 2000);
        }}).catch(function(err) {{
            console.error('Copy failed:', err);
            // Fallback vers l'ancienne méthode
            fallbackCopy_{idx}(text);
        }});
    }} else {{
        // Fallback pour navigateurs plus anciens
        fallbackCopy_{idx}(text);
    }}
}}

function fallbackCopy_{idx}(text) {{
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    
    try {{
        const successful = document.execCommand('copy');
        if (successful) {{
            const btn = event.target;
            const originalText = btn.textContent;
            btn.textContent = '✅ Copied!';
            btn.style.backgroundColor = '#28a745';
            
            setTimeout(function() {{
                btn.textContent = originalText;
                btn.style.backgroundColor = '#007bff';
            }}, 2000);
        }} else {{
            alert('Failed to copy to clipboard');
        }}
    }} catch (err) {{
        console.error('Fallback copy failed:', err);
        alert('Copy not supported in this browser');
    }}
    
    document.body.removeChild(textarea);
}}
"""    

    
    html += """
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderMath);
} else {
    renderMath();
}

setTimeout(renderMath, 100);
setTimeout(renderMath, 500); // Double sécurité

// Additional safety: re-apply proper styling to math elements
setTimeout(() => {
    // Fix for inline math (not inside display math)
    document.querySelectorAll('.katex').forEach(el => {
        // Check if this is inline math (not inside a display math container)
        if (!el.closest('.katex-display')) {
            el.style.direction = 'ltr';
            el.style.unicodeBidi = 'embed';
        }
    });
    
    // Display math - centered but LTR
    document.querySelectorAll('.katex-display').forEach(el => {
        el.style.direction = 'ltr';
        el.style.textAlign = 'center';
        el.style.unicodeBidi = 'embed';
        el.style.marginLeft = 'auto';
        el.style.marginRight = 'auto';
        el.style.display = 'block';
    });
}, 1000);
</script>
</body>
</html>"""
    
    return html



def contains_arabic(text):
    """
    Détecte si le texte contient des caractères arabes.
    
    Args:
        text: Texte à analyser
        
    Returns:
        bool: True si le texte contient de l'arabe
    """
    import re
    # Plage Unicode pour les caractères arabes
    arabic_regex = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
    return bool(arabic_regex.search(text))

# Test si exécuté directement
if __name__ == '__main__':
    #print("🧪 Test du module katex_loader...\n")
    
    try:
        # Test de chargement
        css, js, autorender = load_katex_inline()
        # print(f"\n✅ Chargement réussi!")
        # print(f"   CSS: {len(css):,} caractères")
        # print(f"   JS: {len(js):,} caractères")
        # print(f"   Auto-render: {len(autorender):,} caractères")
        
        # Test de génération HTML avec matrice et boutons de copie
        test_history = [
            {
                'sender': 'You',
                'message': 'Peux-tu résoudre $x^2 + 2x + 1 = 0$ ?',
                'timestamp': '10:00:00'
            },
            {
                'sender': 'AI',
                'message': 'Bien sûr! La solution est:\n\\begin{solution}\n$$x = \\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}$$\nDonc $x = -1$ (racine double)\n\\end{solution}',
                'timestamp': '10:00:15'
            },
            {
                'sender': 'AI',
                'message': '\\begin{solution}\nEt voici une matrice:\n\\[ L = \\begin{pmatrix} 1 & 0 \\\\ l_{21} & 1 \\end{pmatrix} \\]\n\\end{solution}',
                'timestamp': '10:00:30'
            },
            {
                'sender': 'You', 
                'message': 'Super! Et pour les matrices plus grandes?\n\\[ A = \\begin{pmatrix} a & b & c \\\\ d & e & f \\\\ g & h & i \\end{pmatrix} \\]',
                'timestamp': '10:01:00'
            }
        ]
        
        html = build_chat_html_with_katex(test_history)
        
        # Sauvegarder pour test
        # output_file = 'test_katex_chat_with_copy.html'
        # with open(output_file, 'w', encoding='utf-8') as f:
            # f.write(html)
        
        # print(f"\n✅ HTML généré: {len(html):,} caractères")
        # print(f"✅ Fichier sauvegardé: {output_file}")
        # print(f"\n👉 Ouvrez {output_file} dans un navigateur pour vérifier le rendu et les boutons de copie")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()