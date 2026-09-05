import cv2
from pathlib import Path

img = cv2.imread(r"C:\Users\josef\AppData\Local\Temp\opencode\pg11_300dpi.png")
outdir = Path(r"C:\Users\josef\OneDrive\Universidad\10mo Semestre\MCOC\Proyecto 1\P1\Proyecto_Edificio_Ingenieria\resultados\cargas_disponibles\evidencia_ocr")
outdir.mkdir(parents=True, exist_ok=True)

crops = {
    "P1_2800":            (7700, 5350, 8100, 5600),
    "P4_350_100":         (1250, 9050, 3000, 9350),
    "P4_200_200":         (2800, 9050, 3400, 9350),
    "P4_LINEAL_7600":     (4050, 9100, 4350, 9350),
    "P2_DOT_13000":       (12800, 2480, 13500, 2660),
    "P3_DOT_W_6700":      (9250, 7300, 9800, 7500),
    "P3_DOT_E_6000":      (13000, 7380, 13400, 7520),
    "PISO_1S_CUADROS":    (300, 4200, 3000, 5480),
    "PISO_1_CUADROS":     (4400, 4300, 8200, 5620),
    "PISO_2_CUADROS":     (9500, 3450, 13200, 4720),
    "PISO_3_CUADROS":     (9000, 8400, 13000, 9460),
    "PISO_4_CUADROS":     (600, 8930, 4650, 9360),
}
H, W = img.shape[:2]
for name, (x0, y0, x1, y1) in crops.items():
    x0 = max(0, x0); y0 = max(0, y0); x1 = min(W, x1); y1 = min(H, y1)
    crop = img[y0:y1, x0:x1]
    cv2.imwrite(str(outdir / f"{name}.png"), crop)
    print(name, crop.shape)
print("DIR", outdir)