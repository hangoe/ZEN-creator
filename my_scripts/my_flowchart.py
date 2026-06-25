"""Generate a Mermaid flowchart showing the industry heat data flow.

Produces:
  outputs/flowchart/industry_heat_dataflow.mmd  (Mermaid source)
  outputs/flowchart/industry_heat_dataflow.png  (if mmdc is installed)

Install mermaid-cli to render PNG:
  npm install -g @mermaid-js/mermaid-cli
"""

import shutil
import subprocess
from pathlib import Path

OUT_DIR = Path(__file__).parent.parent / "outputs" / "flowchart"
MMD_FILE = OUT_DIR / "industry_heat_dataflow.mmd"
PNG_FILE = OUT_DIR / "industry_heat_dataflow.png"

DIAGRAM = r"""%%{init: {
  "theme": "base",
  "flowchart": {"rankSpacing": 50, "nodeSpacing": 12, "subGraphTitleMargin": {"top": 5, "bottom": 5}},
  "themeVariables": {
    "primaryColor": "#e8f4f8",
    "primaryBorderColor": "#2c7bb6",
    "secondaryColor": "#fff7e6",
    "secondaryBorderColor": "#d95f0e",
    "lineColor": "#555555",
    "fontSize": "12px"
  }
}}%%

flowchart TB

  %% ===== DATA SOURCES =====
  subgraph DATA["Data Sources"]
    direction LR
    R2017[("Rehfeldt2017")] ~~~ A2023[("AIDRES2023")] ~~~ W2017[("Wolf2017")] ~~~ PROC_XL[("process_param.xlsx")] ~~~ JRC_ET[("JRC-EU-TIMES")]
    HEAT_XL[("heat_tech_param.xlsx")] ~~~ CARR_XL[("industry_carriers.xlsx")] ~~~ IDEES[("JRC-IDEES-2023")] ~~~ FAO[("FAOSTAT")] ~~~ EURO[("Eurostat")] ~~~ M2024[("Mayer2024")]
  end

  %% ===== DATASET CLASSES =====
  subgraph DS["Dataset Classes"]
    direction LR
    PP["<b>ProcessParametrization</b><br/><i>sector params, fuel shares,<br/>heat CFs, costs</i>"]
    HTP["<b>HeatTechParam.</b><br/><i>boiler &amp; HP<br/>params</i>"]
    ICD["<b>IndustryCarrier</b><br/><i>carrier<br/>attributes</i>"]
    JID["<b>JrcIdees</b><br/><i>capacity &amp;<br/>demand</i>"]
    FFD["<b>Faostat</b><br/><i>food cap.<br/>&amp; demand</i>"]
    EBD["<b>Eurostat</b><br/><i>boiler<br/>capacity</i>"]
    M24["<b>Mayer2024</b><br/><i>TES<br/>params</i>"]
  end

  %% ===== ELEMENT CLASSES =====
  subgraph ELEM["IndustryHeat Sector — 27 Elements"]
    direction LR

    subgraph CARR["Carriers"]
      direction TB
      C_GL["glass"]
      C_CE["ceramic"]
      C_PA["paper"]
      C_FO["food"]
      C_H1["heat 0-100"]
      C_H2["heat 100-150"]
      C_H3["heat 150-200"]
    end

    subgraph PROD["Production"]
      direction TB
      P_GL["glass prod."]
      P_CE["ceramic prod."]
      P_PA["paper prod."]
      P_FO["food prod."]
    end

    subgraph HEAT["Heat Supply"]
      direction TB
      HP1["HP 0-100"]
      HP2["HP 100-150"]
      HP3["HP 150-200"]
      B1["biomass boiler"]
      B2["electrode boiler"]
      B3["NG boiler"]
      TC1["temp conv 150"]
      TC2["temp conv 100"]
    end

    subgraph TES["TES"]
      direction TB
      TW1["water 0-100"]
      TW2["water 100-150"]
      TS1["steam 100-150"]
      TS2["steam 150-200"]
    end

    subgraph DSM["DSM"]
      direction TB
      D1["glass"]
      D2["ceramic"]
      D3["paper"]
      D4["food"]
    end
  end

  %% ===== DATA → DATASETS =====
  R2017 & A2023 & W2017 & PROC_XL & JRC_ET --> PP
  IDEES -.->|fuel shares| PP
  HEAT_XL --> HTP
  CARR_XL --> ICD
  IDEES --> JID
  FAO --> FFD
  EURO --> EBD
  M2024 --> M24

  %% ===== DATASETS → ELEMENTS =====
  PP --> PROD & HEAT
  ICD --> CARR
  JID --> CARR & PROD
  FFD --> C_FO & P_FO
  HTP --> HEAT
  EBD --> HEAT
  M24 --> TES

  %% ===== STYLING =====
  classDef dataSource fill:#fff7e6,stroke:#d95f0e,stroke-width:1px
  classDef dataset fill:#e8f4f8,stroke:#2c7bb6,stroke-width:2px
  classDef element fill:#e8f8e8,stroke:#2ca02c,stroke-width:1px

  class R2017,A2023,W2017,PROC_XL,HEAT_XL,CARR_XL,M2024,IDEES,FAO,EURO,JRC_ET dataSource
  class PP,HTP,ICD,JID,FFD,EBD,M24 dataset
  class C_GL,C_CE,C_PA,C_FO,C_H1,C_H2,C_H3 element
  class P_GL,P_CE,P_PA,P_FO element
  class HP1,HP2,HP3,B1,B2,B3,TC1,TC2 element
  class TW1,TW2,TS1,TS2,D1,D2,D3,D4 element
"""


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    MMD_FILE.write_text(DIAGRAM)
    print(f"Mermaid source written to {MMD_FILE}")

    if shutil.which("mmdc"):
        subprocess.run(
            ["mmdc", "-i", str(MMD_FILE), "-o", str(PNG_FILE), "-w", "2400", "-H", "1200"],
            check=True,
        )
        print(f"PNG rendered to {PNG_FILE}")
    else:
        print(
            "mmdc not found — install mermaid-cli to render PNG:\n"
            "  npm install -g @mermaid-js/mermaid-cli\n"
            f"  mmdc -i {MMD_FILE} -o {PNG_FILE}"
        )
        print(f"\nYou can also paste the .mmd file content into https://mermaid.live")


if __name__ == "__main__":
    main()
