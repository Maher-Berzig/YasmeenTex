"""
latex_renderer.py: LaTeX preprocessing and KaTeX rendering utilities.
Handles conversion of LaTeX to HTML-friendly format for web display.
"""
import re
import os
from PyQt5.QtCore import QUrl
from katex_loader import load_katex_inline  # ✅ Import correct


def get_katex_base_url():
    """Get base URL for local KaTeX files."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    katex_dir = os.path.join(script_dir, 'katex')
    return QUrl.fromLocalFile(katex_dir + os.sep)


class LaTeXProcessor:
    """Handles LaTeX preprocessing and conversion for KaTeX rendering."""

    @staticmethod
    def preprocess_latex_text(text: str) -> str:
        if not text:
            return ""
            
        # STEP 0: Wrap align / align* in $$...$$ if not already inside $$...$$
        def wrap_align_env(match):
            content = match.group(0)
            if content.strip().startswith("$$"):
                return content
            return f"$$\n{content}\n$$"

        text = re.sub(r'\\begin\{align\*\}.*?\\end\{align\*\}', wrap_align_env, text, flags=re.DOTALL)
        text = re.sub(r'\\begin\{align\}.*?\\end\{align\}', wrap_align_env, text, flags=re.DOTALL)

        # STEP 1: Convert cases to array
        def handle_cases(match):
            content = match.group(1).strip()
            return f'\\left\\{{\\begin{{array}}{{ll}}{content}\\end{{array}}\\right.'

        def handle_cases_star(match):
            content = match.group(1).strip()
            return f'\\left\\{{\\begin{{array}}{{cc}}{content}\\end{{array}}\\right.'

        text = re.sub(r'\\begin\{cases\}(.*?)\\end\{cases\}', handle_cases, text, flags=re.DOTALL)
        text = re.sub(r'\\begin\{cases\*\}(.*?)\\end\{cases\*\}', handle_cases_star, text, flags=re.DOTALL)

        # STEP 2: Extract ALL math into placeholders
        math_blocks = []

        def save_math(m):
            math_blocks.append(m.group(0))
            return f"§MATH{len(math_blocks) - 1}§"

        # Order matters: handle $$, \[ \], \( \), then $
        text = re.sub(r'\$\$(?!\$)(.*?)(?<!\$)\$\$', save_math, text, flags=re.DOTALL)
        text = re.sub(r'\\\[(.*?)\\\]', save_math, text, flags=re.DOTALL)
        text = re.sub(r'\\\((.*?)\\\)', save_math, text, flags=re.DOTALL)

        def handle_inline_math(m):
            content = m.group(1)
            if "\n" in content:
                math_blocks.append(f"$${content}$$")
            else:
                math_blocks.append(f"${content}$")
            return f"§MATH{len(math_blocks) - 1}§"

        text = re.sub(r'(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)', handle_inline_math, text, flags=re.DOTALL)

        # STEP 3: Handle enumerate with nesting
        def handle_enumerate_with_nesting(text: str) -> str:
            """Convert nested \begin{enumerate}...\end{enumerate} to <ol> with depth classes."""
            depth = 0
            result = []
            i = 0
            n = len(text)
            
            while i < n:
                if text.startswith(r'\begin{enumerate}', i):
                    j = i + len(r'\begin{enumerate}')
                    if j < n and text[j] == '[':
                        while j < n and text[j] != ']':
                            j += 1
                        j += 1
                    depth += 1
                    class_attr = f' class="enum-level-{depth}"' if depth > 1 else ''
                    result.append(f'<ol{class_attr}>')
                    i = j
                elif text.startswith(r'\end{enumerate}', i):
                    result.append('</ol>')
                    depth = max(0, depth - 1)
                    i += len(r'\end{enumerate}')
                elif text.startswith(r'\item', i):
                    j = i + len(r'\item')
                    while j < n and text[j] in ' \t':
                        j += 1
                    if j < n and text[j] == '[':
                        while j < n and text[j] != ']':
                            j += 1
                        j += 1
                        while j < n and text[j] in ' \t':
                            j += 1
                    result.append('<li>')
                    i = j
                else:
                    result.append(text[i])
                    i += 1
            
            return ''.join(result)

        text = handle_enumerate_with_nesting(text)

        # Handle itemize
        text = re.sub(r'\\begin{itemize}', '<ul>', text)
        text = re.sub(r'\\end{itemize}', '</ul>', text)
        text = re.sub(r'\\item\s*(?!\[)', '<li>', text)
        text = re.sub(r'(<li>.*?)(?=(<li>|</ul>|</ol>|$))', r'\1</li>', text, flags=re.DOTALL)    

        # Description lists
        def handle_description(match):
            content = match.group(1)
            items = re.findall(r'\\item\[([^\]]+)\]\s*([^\\]*?)(?=\\item\[|$)', content, re.DOTALL)
            html = '<dl>'
            for term, desc in items:
                html += f'<dt><strong>{term}</strong></dt><dd>{desc.strip()}</dd>'
            html += '</dl>'
            return html
        text = re.sub(r'\\begin\{description\}(.*?)\\end\{description\}', handle_description, text, flags=re.DOTALL)

        # Theorems
        def handle_theorem(match):
            env_type = match.group(1)
            content = match.group(2)
            title_map = {
                'theorem': 'Théorème',
                'lemma': 'Lemme',
                'proposition': 'Proposition',
                'corollary': 'Corollaire',
                'definition': 'Définition',
                'example': 'Exemple',
                'remark': 'Remarque',
                'proof': 'Preuve'
            }
            title = title_map.get(env_type, env_type.capitalize())
            return f'<div class="theorem-box"><strong>{title}:</strong> {content}</div>'
        
        theorem_envs = '|'.join(['theorem', 'lemma', 'proposition', 'corollary', 'definition', 'example', 'remark', 'proof'])
        text = re.sub(rf'\\begin\{{({theorem_envs})\}}(.*?)\\end\{{\1\}}', handle_theorem, text, flags=re.DOTALL)

        # Text formatting
        text = re.sub(r'\\textbf\{([^}]+)\}', r'<strong>\1</strong>', text)
        text = re.sub(r'\\bf\{([^}]+)\}', r'<strong>\1</strong>', text)
        text = re.sub(r'\\textit\{([^}]+)\}', r'<em>\1</em>', text)
        text = re.sub(r'\\emph\{([^}]+)\}', r'<em>\1</em>', text)
        text = re.sub(r'\\it\{([^}]+)\}', r'<em>\1</em>', text)
        text = re.sub(r'\\underline\{([^}]+)\}', r'<u>\1</u>', text)
        text = re.sub(r'\\texttt\{([^}]+)\}', r'<code>\1</code>', text)
        text = re.sub(r'\\verb\|([^|]+)\|', r'<code>\1</code>', text)

        # Sections
        text = re.sub(r'\\section\*?\{([^}]+)\}', r'<h3>\1</h3>', text)
        text = re.sub(r'\\subsection\*?\{([^}]+)\}', r'<h4>\1</h4>', text)
        text = re.sub(r'\\subsubsection\*?\{([^}]+)\}', r'<h5>\1</h5>', text)
        text = re.sub(r'\\par\s+', '<br><br>', text)
        text = re.sub(r'\n\s*\n', '<br><br>', text)

        # Tables
        def handle_table(match):
            content = match.group(1)
            rows = [r.strip() for r in content.split('\\\\') if r.strip()]
            html = '<table class="latex-table"><tbody>'
            for row in rows:
                cells = [c.strip() for c in row.split('&')]
                html += '<tr>' + ''.join(f'<td>{cell}</td>' for cell in cells) + '</tr>'
            html += '</tbody></table>'
            return html
        text = re.sub(r'\\begin\{tabular\}\{[^}]+\}(.*?)\\end\{tabular\}', handle_table, text, flags=re.DOTALL)

        # Quotes, verbatim
        text = re.sub(r'\\begin\{quote\}(.*?)\\end\{quote\}', r'<blockquote>\1</blockquote>', text, flags=re.DOTALL)
        text = re.sub(r'\\begin\{verbatim\}(.*?)\\end\{verbatim\}', r'<pre>\1</pre>', text, flags=re.DOTALL)

        # Special chars
        text = text.replace('\\&', '&amp;')
        text = text.replace('\\%', '%')
        text = text.replace('\\$', '$')
        text = text.replace('\\#', '#')
        text = text.replace('\\_', '_')
        text = text.replace('\\{', '{')
        text = text.replace('\\}', '}')
        text = text.replace('\\quad', '&nbsp;&nbsp;&nbsp;&nbsp;')
        text = text.replace('\\qquad', '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;')
        text = text.replace('~', '&nbsp;')

        # STEP 4: Restore math blocks
        for i, block in enumerate(math_blocks):
            text = text.replace(f"§MATH{i}§", block)

        # STEP 5: Final cleanup
        text = re.sub(r'\\left{', r'\\left\\{', text)
        text = re.sub(r'\\right}', r'\\right\\}', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'([^\S\r\n]){2,}', ' ', text)
        text = re.sub(r'^\s+|\s+$', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n*(</?(?:ul|ol|li|p|div|br)[^>]*>)\n*', r'\1', text)

        return text
        
    @staticmethod
    def convert_latex_for_katex(text: str) -> str:
        """
        Convert LaTeX math delimiters for KaTeX rendering.
        Only transforms math environments — does NOT alter non-math content.
        """
        if not text:
            return ""
        
        # Protect existing $...$ and $$...$$ by temporarily hiding them
        protected_blocks = []
        
        def save_block(m):
            protected_blocks.append(m.group(0))
            return f"§PROTECTED{len(protected_blocks)-1}§"
        
        # Save existing $...$ and $$...$$
        text = re.sub(r'\$\$(?!\$)(.*?)(?<!\$)\$\$', save_block, text, flags=re.DOTALL)
        text = re.sub(r'(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)', save_block, text, flags=re.DOTALL)
        
        # Convert \[...\] and \(...\)
        text = re.sub(r'\\\[(.*?)\\\]', 
                     lambda m: f"$${m.group(1).strip()}$$", 
                     text, flags=re.DOTALL)
        
        text = re.sub(r'\\\((.*?)\\\)', 
                     lambda m: f"${m.group(1).strip()}$", 
                     text, flags=re.DOTALL)
        
        # Restore protected blocks
        for i, block in enumerate(protected_blocks):
            text = text.replace(f"§PROTECTED{i}§", block)
        
        return text
        
    def generate_katex_html(latex_content: str, title: str = "", current_language: str = "en") -> str:
        """
        Generate complete HTML document with KaTeX rendering using inline base64.
        
        Args:
            latex_content: Raw LaTeX content
            title: Optional title for the content
            current_language: Current application language ('en', 'fr', 'ar')
            
        Returns:
            Complete HTML document string
        """
        if not latex_content:
            return """<!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family:'Segoe UI',sans-serif; padding:20px; color:#333;">
    <p style="color:#999; font-style:italic;">No content to display</p>
    </body>
    </html>"""
        
        # ✅ Charger KaTeX en base64
        css_content, katex_js, autorender_js = load_katex_inline()
        
        # ✅ Prétraiter le LaTeX
        processed = LaTeXProcessor.preprocess_latex_text(latex_content)
        processed = LaTeXProcessor.convert_latex_for_katex(processed)
        
        # ✅ Déterminer la direction basée sur la langue de l'application
        if current_language == 'ar':
            text_direction = "rtl"
            text_align = "right"
            body_class = "rtl-content"
        else:
            text_direction = "ltr"
            text_align = "left"
            body_class = "ltr-content"
        
        # ✅ Titre
        title_html = f'<h2>{title}</h2>' if title else ''
        
        # ✅ HTML complet avec KaTeX inline et support RTL
        html_doc = f"""<!DOCTYPE html>
    <html dir="{text_direction}">
    <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
    /* KaTeX CSS embarqué */
    {css_content}

    /* Styles personnalisés */
    body {{
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        margin: 0;
        padding: 20px;
        color: #222;
        background-color: #fff;
        line-height: 1.7;
        font-size: 17px;
        direction: {text_direction};
        text-align: {text_align};
    }}

    /* RTL specific styles */
    body.rtl-content {{
        text-align: right;
        direction: rtl;
        unicode-bidi: plaintext;
    }}

    /* LTR specific styles */
    body.ltr-content {{
        text-align: left;
        direction: ltr;
    }}

    h2 {{
        color: #0078d4;
        border-bottom: 2px solid #0078d4;
        padding-bottom: 10px;
        margin-top: 0;
        margin-bottom: 20px;
    }}

    h3 {{
        color: #106ebe;
        margin-top: 20px;
        margin-bottom: 10px;
        font-size: 1.3em;
    }}

    h4 {{
        color: #2b88d8;
        margin-top: 15px;
        margin-bottom: 8px;
        font-size: 1.15em;
    }}

    h5 {{
        color: #3a9ce0;
        margin-top: 12px;
        margin-bottom: 6px;
        font-size: 1.05em;
    }}

    .content {{
        font-size: 18px;
        line-height: 1.8;
        max-width: 100%;
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
    body.rtl-content .katex .base {{
        direction: ltr;
        unicode-bidi: embed;
    }}

    body.rtl-content .katex .mord {{
        direction: ltr;
    }}

    /* Ensure display math stays centered in RTL containers */
    body.rtl-content .katex-display {{
        text-align: center !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }}

    .katex-display {{
        margin: 1.5em 0;
        overflow-x: auto;
        overflow-y: hidden;
        padding: 10px 0;
    }}

    .katex {{
        font-size: 1.1em;
    }}

    /* Lists styling with RTL support */
    ol {{
        list-style-type: none;
        counter-reset: level1;
        margin: 15px 0;
        padding-{text_align}: 50px;
        position: relative;
    }}

    body.rtl-content ol {{
        padding-right: 50px;
        padding-left: 0;
    }}

    ol li {{
        position: relative;
        padding-{text_align}: 10px;
        margin-bottom: 12px;
    }}

    body.rtl-content ol li {{
        padding-right: 10px;
        padding-left: 0;
    }}

    ol > li {{
        counter-increment: level1;
    }}

    ol > li::before {{
        content: counter(level1) ". ";
        font-weight: bold;
        color: #0078d4;
        position: absolute;
        {text_align}: -40px;
        width: 30px;
        text-align: {text_align};
    }}

    body.rtl-content ol > li::before {{
        right: -40px;
        left: auto;
    }}

    ol ol {{
        counter-reset: level2;
        padding-{text_align}: 50px;
    }}

    body.rtl-content ol ol {{
        padding-right: 50px;
        padding-left: 0;
    }}

    ol ol > li {{
        counter-increment: level2;
    }}

    ol ol > li::before {{
        content: counter(level1) "." counter(level2) " ";
        font-weight: normal;
        color: #106ebe;
        position: absolute;
        {text_align}: -60px;
        width: 45px;
        text-align: {text_align};
    }}

    body.rtl-content ol ol > li::before {{
        right: -60px;
        left: auto;
    }}

    ol ol ol {{
        counter-reset: level3;
        padding-{text_align}: 50px;
    }}

    body.rtl-content ol ol ol {{
        padding-right: 50px;
        padding-left: 0;
    }}

    ol ol ol > li {{
        counter-increment: level3;
    }}

    ol ol ol > li::before {{
        content: counter(level1) "." counter(level2) "." counter(level3) " ";
        {text_align}: -75px;
        width: 60px;
    }}

    body.rtl-content ol ol ol > li::before {{
        right: -75px;
        left: auto;
    }}

    ul {{
        margin: 15px 0;
        padding-{text_align}: 40px;
    }}

    body.rtl-content ul {{
        padding-right: 40px;
        padding-left: 0;
    }}

    ul li {{
        margin-bottom: 8px;
    }}

    dl {{
        margin: 15px 0;
    }}

    dt {{
        font-weight: bold;
        color: #0078d4;
        margin-top: 10px;
    }}

    dd {{
        margin-{text_align}: 25px;
        margin-bottom: 10px;
    }}

    body.rtl-content dd {{
        margin-right: 25px;
        margin-left: 0;
    }}

    p {{
        margin: 1em 0;
    }}

    strong {{
        color: #0078d4;
        font-weight: 600;
    }}

    em {{
        color: #333;
        font-style: italic;
    }}

    code {{
        background-color: #f5f5f5;
        padding: 2px 6px;
        border-radius: 3px;
        font-family: 'Courier New', monospace;
        font-size: 0.9em;
        color: #d73a49;
    }}

    pre {{
        background-color: #f5f5f5;
        padding: 15px;
        border-radius: 5px;
        border-{text_align}: 4px solid #0078d4;
        overflow-x: auto;
        font-family: 'Courier New', monospace;
        font-size: 0.9em;
    }}

    body.rtl-content pre {{
        border-right: 4px solid #0078d4;
        border-left: none;
    }}

    blockquote {{
        margin: 15px 0;
        padding: 10px 20px;
        border-{text_align}: 4px solid #0078d4;
        background-color: #f9f9f9;
        font-style: italic;
        color: #555;
    }}

    body.rtl-content blockquote {{
        border-right: 4px solid #0078d4;
        border-left: none;
    }}

    .theorem-box {{
        margin: 20px 0;
        padding: 15px;
        border: 2px solid #0078d4;
        border-radius: 5px;
        background-color: #f0f8ff;
    }}

    .theorem-box strong {{
        color: #0078d4;
        font-size: 1.1em;
    }}

    .latex-table {{
        border-collapse: collapse;
        margin: 20px auto;
        min-width: 50%;
    }}

    .latex-table td {{
        border: 1px solid #ddd;
        padding: 10px 15px;
        text-align: center;
    }}

    .latex-table tr:nth-child(even) {{
        background-color: #f9f9f9;
    }}

    .latex-table tr:hover {{
        background-color: #f0f8ff;
    }}

    ::-webkit-scrollbar {{
        width: 10px;
        height: 10px;
    }}

    ::-webkit-scrollbar-track {{
        background: #f1f1f1;
        border-radius: 5px;
    }}

    ::-webkit-scrollbar-thumb {{
        background: #888;
        border-radius: 5px;
    }}

    ::-webkit-scrollbar-thumb:hover {{
        background: #555;
    }}

    .katex-display > .katex {{
        text-align: center;
    }}

    @media (max-width: 768px) {{
        body {{
            padding: 10px;
            font-size: 14px;
        }}
        .katex {{
            font-size: 1em;
        }}
    }}
    </style>
    </head>
    <body class="{body_class}">
    {title_html}
    <div class="content">{processed}</div>

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
    console.log('=== KaTeX Exercise Rendering ===');
    console.log('typeof katex:', typeof katex);
    console.log('typeof renderMathInElement:', typeof renderMathInElement);

    function renderMath() {{
        if (typeof renderMathInElement !== 'undefined') {{
            console.log('✅ Début du rendu...');
            try {{
                renderMathInElement(document.body, {{
                    delimiters: [
                        {{left: "$$", right: "$$", display: true}},
                        {{left: "\\[", right: "\\]", display: true}},
                        {{left: "$", right: "$", display: false}},
                        {{left: "\\(", right: "\\)", display: false}}
                    ],
                    throwOnError: false,
                    strict: false,
                    trust: true,
                    macros: {{
                        "\\\\RR": "\\\\mathbb{{R}}",
                        "\\\\NN": "\\\\mathbb{{N}}",
                        "\\\\ZZ": "\\\\mathbb{{Z}}",
                        "\\\\QQ": "\\\\mathbb{{Q}}",
                        "\\\\CC": "\\\\mathbb{{C}}"
                    }}
                }});
                
                // Force proper direction for all math elements after rendering
                document.querySelectorAll('.katex').forEach(el => {{
                    // Check if this is inline math (not inside a display math container)
                    if (!el.closest('.katex-display')) {{
                        el.style.direction = 'ltr';
                        el.style.unicodeBidi = 'embed';
                    }}
                }});
                
                // Display math - centered but LTR
                document.querySelectorAll('.katex-display').forEach(el => {{
                    el.style.direction = 'ltr';
                    el.style.textAlign = 'center';
                    el.style.unicodeBidi = 'embed';
                    el.style.marginLeft = 'auto';
                    el.style.marginRight = 'auto';
                    el.style.display = 'block';
                }});
                
                console.log('✅ Rendu terminé!');
            }} catch(e) {{
                console.error('❌ Erreur:', e);
            }}
        }} else {{
            console.error('❌ renderMathInElement non disponible');
        }}
    }}

    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', renderMath);
    }} else {{
        renderMath();
    }}

    setTimeout(renderMath, 100);

    // Additional safety: re-apply proper styling to math elements
    setTimeout(() => {{
        // Fix for inline math (not inside display math)
        document.querySelectorAll('.katex').forEach(el => {{
            // Check if this is inline math (not inside a display math container)
            if (!el.closest('.katex-display')) {{
                el.style.direction = 'ltr';
                el.style.unicodeBidi = 'embed';
            }}
        }});
        
        // Display math - centered but LTR
        document.querySelectorAll('.katex-display').forEach(el => {{
            el.style.direction = 'ltr';
            el.style.textAlign = 'center';
            el.style.unicodeBidi = 'embed';
            el.style.marginLeft = 'auto';
            el.style.marginRight = 'auto';
            el.style.display = 'block';
        }});
    }}, 1000);
    </script>
    </body>
    </html>"""
        
        return html_doc

class KaTeXRenderer:
    """Wrapper for rendering LaTeX in QWebEngineView."""
    
    @staticmethod
    def render(web_view, latex_content: str, title: str = "", current_language: str = "en"):
        """
        Render LaTeX content in a QWebEngineView widget.
        
        Args:
            web_view: QWebEngineView instance
            latex_content: LaTeX text to render
            title: Optional title for the content
            current_language: Current application language ('en', 'fr', 'ar')
        """
        html_doc = LaTeXProcessor.generate_katex_html(latex_content, title, current_language)
        web_view.setHtml(html_doc, QUrl("about:blank"))