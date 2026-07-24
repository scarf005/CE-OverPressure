#load "../Source/CEOverPressure/PressureModel.fs"

open CEOverPressure

let assertNear expected actual tolerance message =
    if abs (expected - actual) > tolerance then
        failwithf "%s: expected %f, got %f" message expected actual

assertNear 2.2f (PressureModel.estimateYieldKg 217) 0.0001f "105 mm reference yield"
assertNear 0.0f (PressureModel.estimateYieldKg 0) 0.0f "zero damage yield"
assertNear 65.2937f (PressureModel.peakPressureKPa 4.0f 2.2f) 0.01f "105 mm pressure at four metres"
assertNear 88.1465f (PressureModel.peakPressureKPa 4.0f 2.2f * 1.35f) 0.01f "105 mm outdoor ground reflection"
assertNear 118.9978f (PressureModel.peakPressureKPa 4.0f 2.2f * 1.35f * 1.35f) 0.01f "105 mm enclosed reflection"
