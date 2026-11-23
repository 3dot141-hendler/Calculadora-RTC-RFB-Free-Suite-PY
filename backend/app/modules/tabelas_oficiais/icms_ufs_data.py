"""Alíquotas modais internas de ICMS por UF (vigência 2026) — fonte única de verdade.

Nota: Representa a alíquota interna geral (modal) de cada Unidade Federativa,
usada como valor inicial sugerido nas simulações de transição 2026–2032.
O contador pode editar livremente no simulador para casos de cesta básica,
alíquota seletiva, substituição tributária ou benefício estadual.
"""

# Tupla: (uf, aliquota_interna, aliquota_fcp, inicio_vigencia, fim_vigencia, fundamentacao)
ICMS_MODAL_UFS_2026: tuple[tuple[str, str, str, str, str | None, str], ...] = (
    ("AC", "19.00", "0.00", "2026-01-01", None, "Lei Complementar Estadual AC (alíquota modal 19%)"),
    ("AL", "19.00", "1.00", "2026-01-01", None, "Lei Estadual AL (19% + 1% FECOEP)"),
    ("AM", "20.00", "0.00", "2026-01-01", None, "Lei Complementar Estadual AM (alíquota modal 20%)"),
    ("AP", "18.00", "0.00", "2026-01-01", None, "Lei Estadual AP (alíquota modal 18%)"),
    ("BA", "20.50", "0.00", "2026-01-01", None, "Lei Estadual BA (alíquota modal 20,5%)"),
    ("CE", "20.00", "0.00", "2026-01-01", None, "Lei Estadual CE (alíquota modal 20%)"),
    ("DF", "20.00", "0.00", "2026-01-01", None, "Lei Distrital DF (alíquota modal 20%)"),
    ("ES", "17.00", "0.00", "2026-01-01", None, "Lei Estadual ES (alíquota modal 17%)"),
    ("GO", "19.00", "0.00", "2026-01-01", None, "Lei Estadual GO (alíquota modal 19%)"),
    ("MA", "23.00", "0.00", "2026-01-01", None, "Lei Estadual MA (alíquota modal 23%)"),
    ("MG", "18.00", "0.00", "2026-01-01", None, "RICMS/MG (alíquota modal 18%)"),
    ("MS", "17.00", "0.00", "2026-01-01", None, "Lei Estadual MS (alíquota modal 17%)"),
    ("MT", "17.00", "0.00", "2026-01-01", None, "Lei Estadual MT (alíquota modal 17%)"),
    ("PA", "19.00", "0.00", "2026-01-01", None, "Lei Estadual PA (alíquota modal 19%)"),
    ("PB", "20.00", "0.00", "2026-01-01", None, "Lei Estadual PB (alíquota modal 20%)"),
    ("PE", "20.50", "0.00", "2026-01-01", None, "Lei Estadual PE (alíquota modal 20,5%)"),
    ("PI", "22.50", "0.00", "2026-01-01", None, "Lei Estadual PI (alíquota modal 22,5%)"),
    ("PR", "19.50", "0.00", "2026-01-01", None, "Lei Estadual PR (alíquota modal 19,5%)"),
    ("RJ", "20.00", "2.00", "2026-01-01", None, "Lei Estadual RJ (20% + 2% FECP)"),
    ("RN", "20.00", "0.00", "2026-01-01", None, "Lei Estadual RN (alíquota modal 20%)"),
    ("RO", "19.50", "0.00", "2026-01-01", None, "Lei Estadual RO (alíquota modal 19,5%)"),
    ("RR", "20.00", "0.00", "2026-01-01", None, "Lei Estadual RR (alíquota modal 20%)"),
    ("RS", "17.00", "0.00", "2026-01-01", None, "Lei Estadual RS (alíquota modal 17%)"),
    ("SC", "17.00", "0.00", "2026-01-01", None, "RICMS/SC (alíquota modal 17%)"),
    ("SE", "19.00", "1.00", "2026-01-01", None, "Lei Estadual SE (19% + 1% FECOEP)"),
    ("SP", "18.00", "0.00", "2026-01-01", None, "RICMS/SP (alíquota modal 18%)"),
    ("TO", "20.00", "0.00", "2026-01-01", None, "Lei Estadual TO (alíquota modal 20%)"),
)
