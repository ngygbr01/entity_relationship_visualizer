import json
from pyvis.network import Network
import os
import webbrowser

class WarehouseClickVisualizer:
    def __init__(self):
        # A gráf inicializálása
        self.net = Network(
            height="100vh", 
            width="100%", 
            bgcolor="#222222", 
            font_color="white", 
            select_menu=True,
            cdn_resources="in_line"
        )
        self.data = {}
        
    def load_data(self, filename):
        if not os.path.exists(filename):
            print(f"[HIBA] '{filename}' nem található!")
            return False
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            print("[-] Adatok betöltve.")
            return True
        except Exception as e:
            print(f"[HIBA] {e}")
            return False

    def build_graph(self):
        config = self.data.get("warehouse_config", {"racks": 1, "levels": 1, "bins_per_level": 1})
        bins_list = self.data.get("bins", [])
        # Gyorskereső szótár készítése a dobozok tartalmához
        loaded_bins = {b['id']: b['contents'] for b in bins_list}

        print("[-] Gráf építése...")

        for r in range(1, config['racks'] + 1):
            rack_id = f"Polc {r}"
            # Fő polc létrehozása
            self.net.add_node(rack_id, label=rack_id, color="#ff9f1c", shape="box", font={'size': 30, 'face':'Arial'}, level=0)

            for l in range(1, config['levels'] + 1):
                prev_bin_id = None
                for b in range(1, config['bins_per_level'] + 1):
                    bin_full_id = f"R{r}-L{l}-B{b}"
                    contents = loaded_bins.get(bin_full_id, [])
                    
                    # --- HTML TARTALOM GENERÁLÁSA (Ez jelenik meg a felugró ablakban) ---
                    if contents:
                        status_color = "#2ec4b6" # Türkiz (Van benne valami)
                        
                        # Modern HTML táblázat a popup ablakhoz
                        popup_html = f"""
                        <h2 style='margin-top:0; color:#ff9f1c;'>📦 {bin_full_id} tartalma</h2>
                        <table style='width:100%; border-collapse: collapse; font-family: Arial; color: #ddd;'>
                            <tr style='background-color: #444; text-align: left;'>
                                <th style='padding: 8px;'>Termék megnevezése</th>
                                <th style='padding: 8px; text-align: right;'>Mennyiség</th>
                            </tr>
                        """
                        for item in contents:
                            popup_html += f"""
                            <tr style='border-bottom: 1px solid #555;'>
                                <td style='padding: 8px;'>{item['name']}</td>
                                <td style='padding: 8px; text-align: right; font-weight:bold; color:#2ec4b6;'>{item['qty']} db</td>
                            </tr>
                            """
                        popup_html += "</table>"
                        
                        label_text = f"{bin_full_id}\n({len(contents)} tétel)"
                    else:
                        status_color = "#4a4e69" # Szürke (Üres)
                        popup_html = f"<h2 style='color:#ccc;'>📭 {bin_full_id}</h2><p>Ez a doboz jelenleg üres.</p>"
                        label_text = bin_full_id

                    # Csomópont hozzáadása
                    # TRÜKK: A 'title' attribútumot használjuk az adattárolásra, de a kattintás fogja előhozni
                    self.net.add_node(
                        bin_full_id, 
                        label=label_text, 
                        title="Kattints a részletekért!", # Hover szöveg (csak infó)
                        popup_data=popup_html,            # EGYEDI MEZŐ: Ezt olvassa majd ki a JavaScript!
                        color=status_color, 
                        shape="box",
                        font={'size': 16, 'face':'Arial'},
                        level=l
                    )

                    # Élek behúzása
                    self.net.add_edge(rack_id, bin_full_id, color='rgba(255,255,255,0.0)')
                    if prev_bin_id:
                        self.net.add_edge(prev_bin_id, bin_full_id, color='gray', width=1)
                    prev_bin_id = bin_full_id

    def save_and_show(self, output_file="raktar_popup.html"):
        # Fizika beállítása
        options = {
            "layout": {"hierarchical": {"enabled": True, "direction": "UD", "sortMethod": "directed", "levelSeparation": 150, "nodeSpacing": 180}},
            "physics": {"hierarchicalRepulsion": {"nodeDistance": 180}, "solver": "hierarchicalRepulsion"},
            "interaction": {"hover": True} # Fontos: engedélyezzük az interakciót
        }
        self.net.set_options(json.dumps(options))
        
        # 1. HTML generálása szövegként
        html_content = self.net.generate_html()

        # 2. EGYEDI JAVASCRIPT ÉS CSS INJEKTÁLÁSA (A Palantir-stílusú ablakhoz)
        # Ez a kód kerül a HTML aljára és kezeli a kattintást
        custom_script = """
        <div id="infoModal" style="display:none; position:fixed; z-index:1000; left:0; top:0; width:100%; height:100%; overflow:auto; background-color:rgba(0,0,0,0.8); backdrop-filter: blur(5px);">
          <div style="background-color:#2a2a2a; margin: 10% auto; padding: 20px; border: 1px solid #444; width: 50%; max-width: 600px; color: white; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.5); font-family: Arial, sans-serif;">
            <span id="closeModal" style="color:#aaa; float:right; font-size:28px; font-weight:bold; cursor:pointer;">&times;</span>
            <div id="modalContent"></div>
            <div style="margin-top:20px; text-align:right;">
                <button onclick="document.getElementById('infoModal').style.display='none'" style="padding:10px 20px; background:#ff9f1c; border:none; color:black; font-weight:bold; cursor:pointer; border-radius:5px;">Bezárás</button>
            </div>
          </div>
        </div>

        <script type="text/javascript">
            // A hálózat betöltődése után rákötjük az eseménykezelőt
            network.on("click", function (params) {
                if (params.nodes.length > 0) {
                    var nodeId = params.nodes[0];
                    // Megkeressük a node adatait a DataSet-ben
                    var nodeData = nodes.get(nodeId);
                    
                    // Ha van 'popup_data' mezője (amit Pythonban adtunk hozzá)
                    if (nodeData.popup_data) {
                        document.getElementById('modalContent').innerHTML = nodeData.popup_data;
                        document.getElementById('infoModal').style.display = "block";
                    }
                }
            });

            // Bezárás gomb (X) működése
            document.getElementById('closeModal').onclick = function() {
                document.getElementById('infoModal').style.display = "none";
            }

            // Ha mellé kattintunk, záródjon be
            window.onclick = function(event) {
                var modal = document.getElementById('infoModal');
                if (event.target == modal) {
                    modal.style.display = "none";
                }
            }
        </script>
        </body>
        """
        
        # Kicseréljük a lezáró </body> taget a mi kódunkra
        final_html = html_content.replace('</body>', custom_script)

        # 3. Mentés UTF-8 kódolással
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(final_html)
            
            filepath = os.path.abspath(output_file)
            webbrowser.open('file://' + filepath)
            print(f"[-] SIKER! Megnyitva: {output_file}")
        except Exception as e:
            print(f"[HIBA] Mentéskor: {e}")

if __name__ == "__main__":
    viz = WarehouseClickVisualizer()
    # Győződj meg róla, hogy az 'adatok.json' ott van a mappában!
    if viz.load_data("adatok.json"):
        viz.build_graph()
        viz.save_and_show()