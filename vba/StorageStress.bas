Attribute VB_Name = "StorageStress"
' European storage adequacy stress test - VBA module for Excel workbooks.
'
' MODEL OVERVIEW:
' Answers operators', regulators', and traders' question: "If it turns cold and stays cold,
' how many days do we have, and what runs out first - the gas, or the ability to move it?"
'
' METHOD:
'   1. Start of a cold spell. Storage stock = the country's peak fill last winter applied
'      to its working volume (AGSI+): a realistic, not hypothetical, inventory.
'   2. Daily flexibility requirement = what the country actually needed on its peak day
'      (storage withdrawal + LNG send-out, both observed), scaled by a severity factor:
'      1.0 = repeat of last winter's worst day; 1.2, 1.4 = colder.
'   3. Each day, LNG send-out supplies up to its observed peak rate; storage covers the
'      remainder, capped by the country's published withdrawal capacity and capped again
'      by what is physically left in the ground.
'   4. Two ways to fail:
'        RATE   - day one. Withdrawal capacity plus send-out cannot meet the daily call
'                 at all. More gas underground would not help; the constraint is GW.
'        VOLUME - day n. The rates are sufficient but the inventory runs out.
'
' WHY SEPARATE THEM:
' They have opposite remedies. A rate-bound system needs compressors, wells, and
' interconnection. A volume-bound system needs more cavern. A single "% full" target
' cannot distinguish the two, which is why it is the wrong instrument for both.
'
' HOW TO IMPORT:
'   1. Open the Excel workbook (or create a new one to test).
'   2. Press Alt+F11 to open the VBA editor.
'   3. In the VBE menu: File > Import File...
'   4. Select StorageStress.bas and click Open.
'   5. The functions are now available as worksheet formulas and in macros.
'
' EXAMPLE USAGE:
'   In a worksheet cell, call BindingDay with your country's parameters:
'     =BindingDay(246.49, 76, 7.067, 0.54, 3.43, 0.54, 1.0)
'   This returns 55, meaning Germany's system binds on day 55 when stressed at 1.0x severity.
'
'   To check what binds:
'     =BindingConstraint(246.49, 76, 7.067, 0.54, 3.43, 0.54, 1.0)
'   Returns "volume", indicating inventory depletion, not rate limits.
'
'   To see the daily flexibility requirement:
'     =DailyCall(3.43, 0.54, 1.0)
'   Returns 3.97 TWh/d.
'
' TO VERIFY:
'   Press Ctrl+Shift+D in the VBE to run SelfTest() and see all tests pass.

Option Explicit

Private Const MAX_DAYS = 200
Private Const TOLERANCE = 0.000000000001  ' 1e-12

' ============ Helper: minimum of two numbers ============
Private Function Min(a As Double, b As Double) As Double
    If a < b Then
        Min = a
    Else
        Min = b
    End If
End Function

' ============ Daily flexibility requirement ============
' Inputs:
'   peakWithdrawalTWhD  - observed peak gas withdrawal (TWh/d)
'   peakLngSendOutTWhD  - observed peak LNG send-out (TWh/d)
'   severity            - stress multiplier (1.0 = last winter, 1.2 = colder, etc.)
' Returns:
'   Daily call in TWh/d: (withdrawal + LNG) * severity
Public Function DailyCall(peakWithdrawalTWhD As Double, peakLngSendOutTWhD As Double, severity As Double) As Double
    DailyCall = (peakWithdrawalTWhD + peakLngSendOutTWhD) * severity
End Function

' ============ Binding day: when does the system fail? ============
' Inputs:
'   workingVolumeTWh    - total working gas storage capacity (TWh)
'   startFillPct        - initial fill level (%, e.g., 76 = 76% full)
'   withdrawalCapTWhD   - maximum rate the country can withdraw from storage (TWh/d)
'   lngCapTWhD          - maximum LNG send-out rate (TWh/d)
'   peakWithdrawalTWhD  - observed peak withdrawal (TWh/d)
'   peakLngSendOutTWhD  - observed peak LNG send-out (TWh/d)
'   severity            - stress multiplier
' Returns:
'   1 if rate-bound on day 1
'   day number (2-200) if volume-bound (inventory depletes)
'   0 if system survives 200 days
Public Function BindingDay(workingVolumeTWh As Double, startFillPct As Double, _
                           withdrawalCapTWhD As Double, lngCapTWhD As Double, _
                           peakWithdrawalTWhD As Double, peakLngSendOutTWhD As Double, _
                           severity As Double) As Long

    Dim call As Double
    Dim lngRate As Double
    Dim fromStorage As Double
    Dim stock As Double
    Dim day As Long

    ' Calculate daily call and how much LNG can supply
    call = DailyCall(peakWithdrawalTWhD, peakLngSendOutTWhD, severity)
    lngRate = Min(lngCapTWhD, call)
    fromStorage = call - lngRate

    ' Check: does withdrawal capacity fail on day 1?
    If fromStorage > withdrawalCapTWhD + TOLERANCE Then
        BindingDay = 1
        Exit Function
    End If

    ' Check: does LNG alone cover the call?
    If fromStorage <= TOLERANCE Then
        BindingDay = 0
        Exit Function
    End If

    ' Simulate: start from initial fill and deplete day by day
    stock = workingVolumeTWh * (startFillPct / 100#)

    For day = 1 To MAX_DAYS
        stock = stock - fromStorage
        If stock <= 0 Then
            BindingDay = day
            Exit Function
        End If
    Next day

    ' Survived 200 days
    BindingDay = 0
End Function

' ============ What constraint binds? ============
' Returns descriptive text matching Python output:
'   "rate"                      - withdrawal capacity insufficient on day 1
'   "volume"                    - inventory runs out within 200 days
'   "none - LNG alone covers it" - no storage needed
'   "none within 200 days"      - all constraints satisfied over 200 days
Public Function BindingConstraint(workingVolumeTWh As Double, startFillPct As Double, _
                                  withdrawalCapTWhD As Double, lngCapTWhD As Double, _
                                  peakWithdrawalTWhD As Double, peakLngSendOutTWhD As Double, _
                                  severity As Double) As String

    Dim call As Double
    Dim lngRate As Double
    Dim fromStorage As Double
    Dim stock As Double
    Dim day As Long

    call = DailyCall(peakWithdrawalTWhD, peakLngSendOutTWhD, severity)
    lngRate = Min(lngCapTWhD, call)
    fromStorage = call - lngRate

    ' Rate-bound
    If fromStorage > withdrawalCapTWhD + TOLERANCE Then
        BindingConstraint = "rate"
        Exit Function
    End If

    ' LNG alone sufficient
    If fromStorage <= TOLERANCE Then
        BindingConstraint = "none - LNG alone covers it"
        Exit Function
    End If

    ' Check volume depletion
    stock = workingVolumeTWh * (startFillPct / 100#)

    For day = 1 To MAX_DAYS
        stock = stock - fromStorage
        If stock <= 0 Then
            BindingConstraint = "volume"
            Exit Function
        End If
    Next day

    ' Survived 200 days
    BindingConstraint = "none within 200 days"
End Function

' ============ Rate shortfall on day 1 ============
' If the system is rate-bound, returns TWh/d by which withdrawal capacity falls short.
' If not rate-bound, returns 0.
Public Function RateShortfall(workingVolumeTWh As Double, startFillPct As Double, _
                              withdrawalCapTWhD As Double, lngCapTWhD As Double, _
                              peakWithdrawalTWhD As Double, peakLngSendOutTWhD As Double, _
                              severity As Double) As Double

    Dim call As Double
    Dim lngRate As Double
    Dim fromStorage As Double

    call = DailyCall(peakWithdrawalTWhD, peakLngSendOutTWhD, severity)
    lngRate = Min(lngCapTWhD, call)
    fromStorage = call - lngRate

    If fromStorage > withdrawalCapTWhD + TOLERANCE Then
        RateShortfall = fromStorage - withdrawalCapTWhD
    Else
        RateShortfall = 0#
    End If
End Function

' ============ Hydrogen physics ============

' Volumetric energy ratio: hydrogen relative to methane per unit volume.
' LHV_H2 = 3.00 kWh/m3; LHV_CH4 = 9.97 kWh/m3
Public Function H2VolumetricRatio() As Double
    H2VolumetricRatio = 3# / 9.97
End Function

' Energy loss factor for EU fleet repurposed to hydrogen.
' Total natural gas capacity = 1100 TWh; hydrogen capacity = 260 TWh
' (Salt caverns 49 + Depleted fields 171 + Aquifers 40)
Public Function H2EnergyLossFactor() As Double
    H2EnergyLossFactor = 1100# / 260#
End Function

' ============ Self-test: known-good cases from Python ============
' Run in the VBE: press F5 or Ctrl+Shift+D, select SelfTest, and click Run.
' Debug output will appear in the Immediate window (Ctrl+G to open).
Public Sub SelfTest()
    Dim callTol As Double
    Dim daysTol As Long

    callTol = 0.01
    daysTol = 0

    Debug.Print "============================================"
    Debug.Print "StorageStress.bas: Self-Test Suite"
    Debug.Print "============================================"

    ' Test 1: Germany, severity 1.0
    ' Params: working_volume=246.49, start_fill=76, withdrawal_cap=7.067,
    '         lng_cap=0.54, peak_withdrawal=3.43, peak_lng=0.54, severity=1.0
    Debug.Print ""
    Debug.Print "[TEST 1] Germany, severity 1.0"
    Debug.Print "  Expected: DailyCall=3.97, Constraint='volume', Day=55"

    Dim t1_call As Double
    t1_call = DailyCall(3.43, 0.54, 1.0)
    Debug.Print "  DailyCall(3.43, 0.54, 1.0) = " & Format(t1_call, "0.00")
    Debug.Assert Abs(t1_call - 3.97) < callTol, _
        "Germany DailyCall failed: expected 3.97, got " & t1_call

    Dim t1_constraint As String
    t1_constraint = BindingConstraint(246.49, 76, 7.067, 0.54, 3.43, 0.54, 1.0)
    Debug.Print "  BindingConstraint = '" & t1_constraint & "'"
    Debug.Assert t1_constraint = "volume", _
        "Germany constraint failed: expected 'volume', got '" & t1_constraint & "'"

    Dim t1_day As Long
    t1_day = BindingDay(246.49, 76, 7.067, 0.54, 3.43, 0.54, 1.0)
    Debug.Print "  BindingDay = " & t1_day
    Debug.Assert t1_day = 55, _
        "Germany BindingDay failed: expected 55, got " & t1_day

    Debug.Print "  [PASS]"

    ' Test 2: Germany, severity 1.2
    Debug.Print ""
    Debug.Print "[TEST 2] Germany, severity 1.2"
    Debug.Print "  Expected: Day=45"

    Dim t2_day As Long
    t2_day = BindingDay(246.49, 76, 7.067, 0.54, 3.43, 0.54, 1.2)
    Debug.Print "  BindingDay = " & t2_day
    Debug.Assert t2_day = 45, _
        "Germany sev 1.2 failed: expected 45, got " & t2_day

    Debug.Print "  [PASS]"

    ' Test 3: Belgium, severity 1.0
    ' Params: working_volume=7.61, start_fill=94, withdrawal_cap=0.16966,
    '         lng_cap=0.72, peak_withdrawal=0.17, peak_lng=0.72, severity=1.0
    Debug.Print ""
    Debug.Print "[TEST 3] Belgium, severity 1.0"
    Debug.Print "  Expected: Constraint='rate', Day=1"

    Dim t3_constraint As String
    t3_constraint = BindingConstraint(7.61, 94, 0.16966, 0.72, 0.17, 0.72, 1.0)
    Debug.Print "  BindingConstraint = '" & t3_constraint & "'"
    Debug.Assert t3_constraint = "rate", _
        "Belgium constraint failed: expected 'rate', got '" & t3_constraint & "'"

    Dim t3_day As Long
    t3_day = BindingDay(7.61, 94, 0.16966, 0.72, 0.17, 0.72, 1.0)
    Debug.Print "  BindingDay = " & t3_day
    Debug.Assert t3_day = 1, _
        "Belgium BindingDay failed: expected 1, got " & t3_day

    Debug.Print "  [PASS]"

    ' Test 4: Spain, severity 1.0
    ' Params: working_volume=35.83, start_fill=87, withdrawal_cap=0.20896,
    '         lng_cap=0.97, peak_withdrawal=0.18, peak_lng=0.97, severity=1.0
    Debug.Print ""
    Debug.Print "[TEST 4] Spain, severity 1.0"
    Debug.Print "  Expected: Constraint='volume', Day=174"

    Dim t4_constraint As String
    t4_constraint = BindingConstraint(35.83, 87, 0.20896, 0.97, 0.18, 0.97, 1.0)
    Debug.Print "  BindingConstraint = '" & t4_constraint & "'"
    Debug.Assert t4_constraint = "volume", _
        "Spain constraint failed: expected 'volume', got '" & t4_constraint & "'"

    Dim t4_day As Long
    t4_day = BindingDay(35.83, 87, 0.20896, 0.97, 0.18, 0.97, 1.0)
    Debug.Print "  BindingDay = " & t4_day
    Debug.Assert t4_day = 174, _
        "Spain BindingDay failed: expected 174, got " & t4_day

    Debug.Print "  [PASS]"

    ' Test 5: Hydrogen functions
    Debug.Print ""
    Debug.Print "[TEST 5] Hydrogen physics"

    Dim h2_ratio As Double
    h2_ratio = H2VolumetricRatio()
    Debug.Print "  H2VolumetricRatio = " & Format(h2_ratio, "0.0000")
    Debug.Assert h2_ratio > 0.25 And h2_ratio < 0.35, _
        "H2VolumetricRatio out of range [0.25, 0.35]: got " & h2_ratio

    Dim h2_loss As Double
    h2_loss = H2EnergyLossFactor()
    Debug.Print "  H2EnergyLossFactor = " & Format(h2_loss, "0.00")
    Debug.Assert h2_loss > 3.0 And h2_loss < 5.0, _
        "H2EnergyLossFactor out of range [3.0, 5.0]: got " & h2_loss

    Debug.Print "  [PASS]"

    Debug.Print ""
    Debug.Print "============================================"
    Debug.Print "ALL TESTS PASSED"
    Debug.Print "============================================"
End Sub
