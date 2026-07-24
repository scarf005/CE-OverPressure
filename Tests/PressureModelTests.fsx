#load "../Source/CEOverPressure/PressureModel.fs"

open System
open System.Globalization
open System.Xml.Linq
open CEOverPressure

let private settings =
    XDocument.Load("Defs/OverpressureSettings.xml").Root.Elements()
    |> Seq.exactlyOne

let private readFloat name =
    settings.Element(XName.Get name).Value
    |> fun value -> Single.Parse(value, CultureInfo.InvariantCulture)

let private parameters =
    { MetresPerCell = readFloat "metresPerCell"
      ReferenceDamage = readFloat "referenceDamage"
      ReferenceYieldKg = readFloat "referenceYieldKg"
      YieldExponent = readFloat "yieldExponent"
      MinimumYieldKg = readFloat "minimumYieldKg"
      MaximumYieldKg = readFloat "maximumYieldKg"
      MinimumPressureYieldKg = readFloat "minimumPressureYieldKg"
      RangeCoefficientMetres = readFloat "rangeCoefficientMetres"
      MinimumScaledDistance = readFloat "minimumScaledDistance"
      CloseRangeLimit = readFloat "closeRangeLimit"
      CloseCubicCoefficient = readFloat "closeCubicCoefficient"
      CloseOffset = readFloat "closeOffset"
      FarLinearCoefficient = readFloat "farLinearCoefficient"
      FarQuadraticCoefficient = readFloat "farQuadraticCoefficient"
      FarCubicCoefficient = readFloat "farCubicCoefficient"
      FarOffset = readFloat "farOffset"
      PressureUnitKPa = readFloat "pressureUnitKPa" }

let assertNear expected actual tolerance message =
    if abs (expected - actual) > tolerance then
        failwithf "%s: expected %f, got %f" message expected actual

assertNear 2.2f (PressureModel.estimateYieldKg parameters 217) 0.0001f "105 mm reference yield"
assertNear 0.0f (PressureModel.estimateYieldKg parameters 0) 0.0f "zero damage yield"
assertNear 65.2937f (PressureModel.peakPressureKPa parameters 4.0f 2.2f) 0.01f "105 mm pressure at four metres"
