from tkinter import *
import pandas as pd
import random
from datetime import datetime, timedelta

alphaDrivers = []
betaDrivers = []
routeOptions = ['из A в B', 'из A в B и обратно']
alphaShiftDuration = 8
betaShiftDuration = 12
routeDurationMin = 60
workStartTime = '06:00'
workFinishTime = '03:00'

def isWeekend(daySelected):
    return daySelected in ['Суббота', 'Воскресенье']
def calcRouteFinish(startTime, duration):
    startDT = datetime.strptime(startTime, "%H:%M")
    endDT = startDT + timedelta(minutes=duration)
    return endDT.strftime("%H:%M")
def unifyInterval(startStr, endStr):
    startDT = datetime.strptime(startStr, "%H:%M")
    endDT = datetime.strptime(endStr, "%H:%M")
    if endDT < startDT:
        endDT += timedelta(days=1)
    return startDT, endDT
def hasTimeInterference(startTime, endTime, busyPeriods):
    startDT, endDT = unifyInterval(startTime, endTime)
    for bStart, bEnd in busyPeriods:
        bStartDT, bEndDT = unifyInterval(bStart, bEnd)
        if startDT < bEndDT and endDT > bStartDT:
            return True
    return False
def findEmptyWindows(driverBusyData, routeDur, breakDur):
    freeWindows = []
    for driver, periods in driverBusyData.items():
        normalized = []
        for (start, end) in periods:
            sDT, eDT = unifyInterval(start, end)
            normalized.append((sDT, eDT))
        normalized.sort(key=lambda x: x[0])
        currentDT = datetime.strptime("06:00", "%H:%M")
        shiftFinish = datetime.strptime("03:00", "%H:%M") + timedelta(days=1)
        for (sDT, eDT) in normalized:
            if (sDT - currentDT).total_seconds()/60 >= routeDur + breakDur:
                freeWindows.append((currentDT.strftime("%H:%M"), sDT.strftime("%H:%M")))
            currentDT = eDT
        if (shiftFinish - currentDT).total_seconds()/60 >= routeDur + breakDur:
            freeWindows.append((currentDT.strftime("%H:%M"), shiftFinish.strftime("%H:%M")))
    return freeWindows
def countExtraDrivers(totalTrips, driversList, shiftLen):
    maxTripsPerDriver = int(shiftLen * 60 / routeDurationMin)
    required = (totalTrips + maxTripsPerDriver - 1) // maxTripsPerDriver
    if len(driversList) >= required:
        return 0
    else:
        return required - len(driversList)
def errorScheduleMessage(textArea, driversList, shiftLen, totalTrips):
    textArea.delete(1.0, END)
    extraNeeded = countExtraDrivers(totalTrips, driversList, shiftLen)
    if extraNeeded > 0:
        textArea.insert(END,("Расписание не может быть создано.\n"
            f"Для продолжения нужно добавить минимум {extraNeeded} водителей "
            "или уменьшить количество рейсов.\n"))
    else:
        textArea.insert(END,("Расписание не может быть создано.\n"
            "Попробуйте уменьшить число рейсов или сократить время маршрута.\n"))
def errorScheduleMessageGA(textArea, driversList, shiftLen, totalTrips):
    textArea.delete(1.0, END)
    extraNeeded = countExtraDrivers(totalTrips, driversList, shiftLen)
    if extraNeeded > 0:
        textArea.insert(END,("Расписание не удалось построить при помощи генетического алгоритма.\n"
            f"Необходимо добавить не менее {extraNeeded} водителей "
            "или уменьшить число рейсов.\n"))
    else:
        textArea.insert(END,("Расписание не удалось построить при помощи генетического алгоритма.\n"
            "Попробуйте сократить время маршрута или число рейсов.\n"))
def canScheduleTrip(startTime, duration, driver, busyData, hoursData, routeCounts, minBreak):
    finish = calcRouteFinish(startTime, duration)
    if hasTimeInterference(startTime, finish, busyData[driver]):
        return False
    if busyData[driver]:
        lastStart, lastEnd = busyData[driver][-1]
        lStartDT = datetime.strptime(lastStart, "%H:%M")
        lEndDT = datetime.strptime(lastEnd, "%H:%M")
        if lEndDT < lStartDT:
            lEndDT += timedelta(days=1)
        candidateDT = datetime.strptime(startTime, "%H:%M")
        if candidateDT < lEndDT:
            return False
        if (candidateDT - lEndDT).total_seconds()/60 < minBreak:
            return False
    if driver in alphaDrivers and hoursData[driver] >= alphaShiftDuration:
        return False
    if driver in betaDrivers and hoursData[driver] >= betaShiftDuration:
        return False
    finDT = datetime.strptime(finish, "%H:%M")
    if finDT < datetime.strptime(startTime, "%H:%M"):
        finDT += timedelta(days=1)
    shiftFinish = datetime.strptime("03:00", "%H:%M") + timedelta(days=1)
    if finDT > shiftFinish:
        return False
    return True
def randomTripAssignment(routeDur, breakDur, minBreak, driversList, busyData, hoursData, routeCount, daySelected):
    for _ in range(50):
        freeSlots = findEmptyWindows(busyData, routeDur, breakDur)
        if not freeSlots:
            return None
        slotStart, slotEnd = random.choice(freeSlots)
        sDT = datetime.strptime(slotStart, "%H:%M")
        eDT = datetime.strptime(slotEnd, "%H:%M")
        if eDT < sDT:
            eDT += timedelta(days=1)
        maxStart = (eDT - sDT).total_seconds()/60 - routeDur
        if maxStart < 0:
            continue
        offset = random.randint(0, int(maxStart))
        candidateDT = sDT + timedelta(minutes=offset)
        candidateTime = candidateDT.strftime("%H:%M")
        random.shuffle(driversList)
        for driver in driversList:
            if driver in alphaDrivers and isWeekend(daySelected):
                continue
            if canScheduleTrip(candidateTime, routeDur, driver, busyData, hoursData, routeCount, minBreak):
                return (driver, candidateTime)
    return None
def createBetterSchedule(driversList, shiftLen, totalTrips, daySelected, textArea, breakDur=10, minBreak=30):
    extraNeeded = countExtraDrivers(totalTrips, driversList, shiftLen)
    if extraNeeded > 0:
        textArea.delete(1.0, END)
        textArea.insert(END,(f"Число водителей недостаточно для {totalTrips} рейсов.\n"
            f"Добавьте минимум {extraNeeded} человек или уменьшите число рейсов.\n"))
        return
    scheduleData = []
    assignedTrips = 0
    activeDrivers = list(driversList)
    random.shuffle(activeDrivers)
    busyList = {driver: [] for driver in activeDrivers}
    hoursList = {driver: 0 for driver in activeDrivers}
    routeCounter = {driver: 0 for driver in activeDrivers}
    currentDT = datetime.strptime("06:00", "%H:%M")
    shiftFinish = datetime.strptime("03:00", "%H:%M") + timedelta(days=1)
    for _ in range(totalTrips):
        chosenType = random.choice(routeOptions)
        realTime = routeDurationMin * 2 if chosenType == 'из A в B и обратно' else routeDurationMin
        startStr = currentDT.strftime("%H:%M")
        endStr = calcRouteFinish(startStr, realTime)
        endDT = datetime.strptime(endStr, "%H:%M")
        if endDT < currentDT:
            endDT += timedelta(days=1)
        if endDT > shiftFinish:
            result = randomTripAssignment(realTime, breakDur, minBreak, activeDrivers, busyList, hoursList, routeCounter, daySelected)
            if result is None:
                errorScheduleMessage(textArea, driversList, shiftLen, totalTrips)
                return
            else:
                driver, slotStart = result
                slotEnd = calcRouteFinish(slotStart, realTime)
                sEndDT = datetime.strptime(slotEnd, "%H:%M")
                if sEndDT < datetime.strptime(slotStart, "%H:%M"):
                    sEndDT += timedelta(days=1)
                spent = (sEndDT - datetime.strptime(slotStart, "%H:%M")).seconds / 60
                routeCounter[driver] += 1
                finalName = chosenType + " (доп. рейс)"
                scheduleData.append({'Водитель': driver,'Тип маршрута': finalName,'Начало': slotStart,'Окончание': slotEnd,'Рейсов за смену': routeCounter[driver]})
                busyList[driver].append((slotStart, slotEnd))
                hoursList[driver] += spent / 60
                assignedTrips += 1
        else:
            placed = False
            random.shuffle(activeDrivers)
            for driver in activeDrivers:
                if driver in alphaDrivers and isWeekend(daySelected):
                    continue
                if canScheduleTrip(startStr, realTime, driver, busyList, hoursList, routeCounter, minBreak):
                    eDT = datetime.strptime(endStr, "%H:%M")
                    usedMin = (eDT - datetime.strptime(startStr, "%H:%M")).seconds / 60
                    routeCounter[driver] += 1
                    scheduleData.append({'Водитель': driver,'Тип маршрута': chosenType,'Начало': startStr,'Окончание': endStr,'Рейсов за смену': routeCounter[driver]})
                    busyList[driver].append((startStr, endStr))
                    hoursList[driver] += usedMin / 60
                    assignedTrips += 1
                    placed = True
                    currentDT = eDT + timedelta(minutes=breakDur + minBreak)
                    break
            if not placed:
                result = randomTripAssignment(realTime, breakDur, minBreak, activeDrivers, busyList, hoursList, routeCounter, daySelected)
                if result is None:
                    errorScheduleMessage(textArea, driversList, shiftLen, totalTrips)
                    return
                else:
                    driver, slotStart = result
                    slotEnd = calcRouteFinish(slotStart, realTime)
                    sEndDT = datetime.strptime(slotEnd, "%H:%M")
                    if sEndDT < datetime.strptime(slotStart, "%H:%M"):
                        sEndDT += timedelta(days=1)
                    spent = (sEndDT - datetime.strptime(slotStart, "%H:%M")).seconds / 60
                    routeCounter[driver] += 1
                    finalName = chosenType + " (доп. рейс)"
                    scheduleData.append({'Водитель': driver,'Тип маршрута': finalName,'Начало': slotStart,'Окончание': slotEnd,'Рейсов за смену': routeCounter[driver]})
                    busyList[driver].append((slotStart, slotEnd))
                    hoursList[driver] += spent / 60
                    assignedTrips += 1
    dfSchedule = pd.DataFrame(scheduleData)
    textArea.delete(1.0, END)
    if not dfSchedule.empty:
        textArea.insert(END, dfSchedule.to_string())
    else:
        errorScheduleMessage(textArea, driversList, shiftLen, totalTrips)
def attemptGeneticSchedule(driversList, shiftLen, totalTrips, daySelected, textArea, breakDur=10, minBreak=30):
    activeDrivers = list(driversList)
    random.shuffle(activeDrivers)
    busyData = {driver: [] for driver in activeDrivers}
    hoursData = {driver: 0 for driver in activeDrivers}
    routeCount = {driver: 0 for driver in activeDrivers}
    scheduleData = []
    assigned = 0
    shiftFinish = datetime.strptime("03:00", "%H:%M") + timedelta(days=1)
    def findWindow(routeTime):
        for _ in range(50):
            freeSlots = findEmptyWindows(busyData, routeTime, breakDur)
            if not freeSlots:
                return None
            slotStart, slotEnd = random.choice(freeSlots)
            sDT = datetime.strptime(slotStart, "%H:%M")
            eDT = datetime.strptime(slotEnd, "%H:%M")
            if eDT < sDT:
                eDT += timedelta(days=1)
            maxStart = (eDT - sDT).total_seconds()/60 - routeTime
            if maxStart < 0:
                continue
            offset = random.randint(0, int(maxStart))
            candidateDT = sDT + timedelta(minutes=offset)
            candidateTime = candidateDT.strftime("%H:%M")
            random.shuffle(activeDrivers)
            for driver in activeDrivers:
                if driver in alphaDrivers and isWeekend(daySelected):
                    continue
                if canScheduleTrip(candidateTime, routeTime, driver, busyData, hoursData, routeCount, minBreak):
                    return (driver, candidateTime)
        return None
    for _ in range(totalTrips):
        chosenType = random.choice(routeOptions)
        realTime = routeDurationMin * 2 if chosenType == 'из A в B и обратно' else routeDurationMin
        tries = 0
        placed = False
        while tries < 50 and not placed:
            tries += 1
            candidateStartDT = datetime.strptime("06:00", "%H:%M")
            if scheduleData:
                lateFinish = datetime.strptime("06:00", "%H:%M")
                for r in scheduleData:
                    rEnd = datetime.strptime(r['Окончание'], "%H:%M")
                    rStart = datetime.strptime(r['Начало'], "%H:%M")
                    if rEnd < rStart:
                        rEnd += timedelta(days=1)
                    if rEnd > lateFinish:
                        lateFinish = rEnd
                candidateStartDT = lateFinish + timedelta(minutes=breakDur + minBreak)
            startStr = candidateStartDT.strftime("%H:%M")
            endStr = calcRouteFinish(startStr, realTime)
            eDT = datetime.strptime(endStr, "%H:%M")
            if eDT < candidateStartDT:
                eDT += timedelta(days=1)
            if eDT > shiftFinish:
                outcome = findWindow(realTime)
                if outcome is not None:
                    driver, slotBegin = outcome
                    slotFinish = calcRouteFinish(slotBegin, realTime)
                    fDT = datetime.strptime(slotFinish, "%H:%M")
                    if fDT < datetime.strptime(slotBegin, "%H:%M"):
                        fDT += timedelta(days=1)
                    used = (fDT - datetime.strptime(slotBegin, "%H:%M")).seconds / 60
                    routeCount[driver] += 1
                    newType = chosenType + " (доп. рейс)"
                    scheduleData.append({'Водитель': driver,'Тип маршрута': newType,'Начало': slotBegin,'Окончание': slotFinish,'Рейсов за смену': routeCount[driver]})
                    busyData[driver].append((slotBegin, slotFinish))
                    hoursData[driver] += used / 60
                    placed = True
                    assigned += 1
            else:
                placedLinear = False
                random.shuffle(activeDrivers)
                for driver in activeDrivers:
                    if driver in alphaDrivers and isWeekend(daySelected):
                        continue
                    if canScheduleTrip(startStr, realTime, driver, busyData, hoursData, routeCount, minBreak):
                        usedTime = (datetime.strptime(endStr, "%H:%M") - datetime.strptime(startStr, "%H:%M")).seconds / 60
                        routeCount[driver] += 1
                        scheduleData.append({'Водитель': driver,'Тип маршрута': chosenType,'Начало': startStr,'Окончание': endStr,'Рейсов за смену': routeCount[driver]})
                        busyData[driver].append((startStr, endStr))
                        hoursData[driver] += usedTime / 60
                        placed = True
                        placedLinear = True
                        break
                if not placedLinear and not placed:
                    outcome = findWindow(realTime)
                    if outcome is not None:
                        driver, slotBegin = outcome
                        slotFinish = calcRouteFinish(slotBegin, realTime)
                        fDT = datetime.strptime(slotFinish, "%H:%M")
                        if fDT < datetime.strptime(slotBegin, "%H:%M"):
                            fDT += timedelta(days=1)
                        used = (fDT - datetime.strptime(slotBegin, "%H:%M")).seconds / 60
                        routeCount[driver] += 1
                        newType = chosenType + " (доп. рейс)"
                        scheduleData.append({'Водитель': driver,'Тип маршрута': newType,'Начало': slotBegin,'Окончание': slotFinish,'Рейсов за смену': routeCount[driver]})
                        busyData[driver].append((slotBegin, slotFinish))
                        hoursData[driver] += used / 60
                        placed = True
                        assigned += 1
        if not placed:
            break
        else:
            assigned += 1
    return scheduleData, assigned
def crossGen(child1, child2):
    midpoint = len(child1)//2
    offspring = child1[:midpoint] + child2[midpoint:]
    return offspring
def mutateGen(offspring):
    if random.random() < 0.1 and len(offspring) > 1:
        i, j = random.sample(range(len(offspring)), 2)
        offspring[i], offspring[j] = offspring[j], offspring[i]
    return offspring
def scheduleFitness(scheduleList, totalTrips, groupA, groupB, routeTime):
    assignedCount = len(scheduleList)
    usedDrivers = set([item['Водитель'] for item in scheduleList])
    driverCount = len(usedDrivers)
    totalMins = sum([(datetime.strptime(item['Окончание'], "%H:%M") - datetime.strptime(item['Начало'], "%H:%M")).seconds / 60 for item in scheduleList])
    avgMins = totalMins / driverCount if driverCount > 0 else 0
    penalty = 0
    for d in usedDrivers:
        dMins = sum([(datetime.strptime(entry['Окончание'], "%H:%M") - datetime.strptime(entry['Начало'], "%H:%M")).seconds / 60 for entry in scheduleList if entry['Водитель'] == d])
        penalty += abs(dMins - avgMins)
    weightTrips = 1000
    weightDrivers = 50
    weightPenalty = 10
    fitness = (assignedCount * weightTrips) - (driverCount * weightDrivers) - (penalty * weightPenalty)
    return fitness
def scheduleByGeneticAlgorithm(driversList, shiftLen, totalTrips, daySelected, textArea, breakDur=10, minBreak=30, generations=10, populationSize=5):
    extraNeeded = countExtraDrivers(totalTrips, driversList, shiftLen)
    if extraNeeded > 0:
        textArea.delete(1.0, END)
        textArea.insert(END,(f"Генетический алгоритм не может построить расписание для {totalTrips} рейсов.\n"
            f"Требуется по меньшей мере {extraNeeded} водителей.\n"
            "Либо уменьшите число рейсов.\n"))
        return
    population = []
    for _ in range(populationSize):
        scheduleSet, _ = attemptGeneticSchedule(driversList, shiftLen, totalTrips, daySelected, textArea, breakDur, minBreak)
        fitVal = scheduleFitness(scheduleSet, totalTrips, alphaDrivers, betaDrivers, routeDurationMin)
        population.append((scheduleSet, fitVal))
    bestSet = None
    bestFit = -float('inf')
    noImprovements = 0
    limitImprovement = 3
    for _ in range(generations):
        scoredPopulation = []
        for individual in population:
            sList = individual[0]
            fVal = scheduleFitness(sList, totalTrips, alphaDrivers, betaDrivers, routeDurationMin)
            scoredPopulation.append((sList, fVal))
        scoredPopulation.sort(key=lambda x: x[1], reverse=True)
        if scoredPopulation[0][1] > bestFit:
            bestFit = scoredPopulation[0][1]
            bestSet = scoredPopulation[0][0]
            noImprovements = 0
        else:
            noImprovements += 1
        if bestFit >= totalTrips * 1000:
            break
        if noImprovements >= limitImprovement:
            break
        newPop = scoredPopulation[:2]
        while len(newPop) < populationSize:
            p1 = random.choice(scoredPopulation)[0]
            p2 = random.choice(scoredPopulation)[0]
            childData = crossGen(p1, p2)
            childData = mutateGen(childData)
            childFit = scheduleFitness(childData, totalTrips, alphaDrivers, betaDrivers, routeDurationMin)
            newPop.append((childData, childFit))
        population = newPop
    textArea.delete(1.0, END)
    if bestSet and len(bestSet) > 0:
        df = pd.DataFrame(bestSet)
        if bestFit >= totalTrips * 1000:
            textArea.insert(END, "Генетический алгоритм успешно нашёл оптимальное решение:\n")
        else:
            textArea.insert(END, "Не удалось достичь оптимума, но найден лучший вариант:\n")
        textArea.insert(END, df.to_string())
    else:
        errorScheduleMessageGA(textArea, driversList, shiftLen, totalTrips)
def genJointSchedule():
    try:
        numTrips = int(routesEntry.get())
        mergedDrivers = alphaDrivers + betaDrivers
        weekday = selectedDay.get()
        if not alphaDrivers and not betaDrivers:
            scheduleResultWidget.insert(END, "\nНет доступных водителей в системе.\n")
            return
        if isWeekend(weekday) and not betaDrivers:
            scheduleResultWidget.insert(END, "\nВ выходные работают только водители типа B, но их нет в системе.\n")
            return
        if isWeekend(weekday) and not alphaDrivers and betaDrivers:
            missing = countExtraDrivers(numTrips, betaDrivers, betaShiftDuration)
            if missing > 0:
                scheduleResultWidget.insert(END,(f"\nНедостаточно водителей типа B для {numTrips} рейсов.\n"
                    f"Необходимо минимум {missing} человек.\n"))
                return
            scheduleResultWidget.insert(END, "\nВодители типа A в выходные не работают. Составляем план для B.\n")
            createBetterSchedule(betaDrivers, betaShiftDuration, numTrips, weekday, scheduleResultWidget)
            return
        combinedLen = max(alphaShiftDuration, betaShiftDuration)
        createBetterSchedule(mergedDrivers, combinedLen, numTrips, weekday, scheduleResultWidget)
    except ValueError:
        scheduleResultWidget.insert(END, "\nВнимание: Введите корректное (целое) число рейсов.\n")
def genJointGeneticSchedule():
    try:
        numTrips = int(routesEntry.get())
        mergedDrivers = alphaDrivers + betaDrivers
        weekday = selectedDay.get()
        if not alphaDrivers and not betaDrivers:
            scheduleResultWidget.insert(END, "\nНет водителей в системе для составления расписания.\n")
            return
        if isWeekend(weekday) and not betaDrivers:
            scheduleResultWidget.insert(END, "\nВ выходные работают только водители типа B, а их нет в системе.\n")
            return
        if isWeekend(weekday) and not alphaDrivers and betaDrivers:
            missing = countExtraDrivers(numTrips, betaDrivers, betaShiftDuration)
            if missing > 0:
                scheduleResultWidget.insert(END,(f"\nНедостаточно водителей типа B для {numTrips} рейсов (выходной).\n"
                    f"Нужно добавить хотя бы {missing} человек.\n"))
                return
            scheduleResultWidget.insert(END, "\nВодители типа A выходные не обслуживают. Используем генетику для B.\n")
            scheduleByGeneticAlgorithm(betaDrivers, betaShiftDuration, numTrips, weekday, scheduleResultWidget, generations=50, populationSize=20)
            return
        combinedLen = max(alphaShiftDuration, betaShiftDuration)
        scheduleByGeneticAlgorithm(mergedDrivers, combinedLen, numTrips, weekday, scheduleResultWidget, generations=50, populationSize=20)
    except ValueError:
        scheduleResultWidget.insert(END, "\nЧисло рейсов должно быть целым. Повторите ввод.\n")
def clearInputs():
    routesEntry.delete(0, END)
    timeEntry.delete(0, END)
    scheduleResultWidget.delete(1.0, END)
    print("\nВсе поля были очищены.\n")
def applyRouteDuration():
    global routeDurationMin
    try:
        routeDurationMin = int(timeEntry.get())
        scheduleResultWidget.insert(END, "\nОсновная длительность маршрута успешно обновлена.\n")
    except ValueError:
        scheduleResultWidget.insert(END, "\nОшибка: Введите целое число минут.\n")
def registerDriver(dNameField, dGroupVar, statusLbl):
    driverName = dNameField.get().strip()
    groupVal = dGroupVar.get()
    if not driverName:
        statusLbl.config(text="Внимание: Имя водителя не может быть пустым.", fg="red")
        return
    if groupVal == "A":
        alphaDrivers.append(driverName)
    else:
        betaDrivers.append(driverName)
    dNameField.delete(0, END)
    statusLbl.config(text=f"Водитель '{driverName}' успешно добавлен (тип {groupVal}).", fg="black")
def runApp():
    global routesEntry, timeEntry, scheduleResultWidget, routeDurationMin, selectedDay
    app = Tk()
    app.title("Регистрация водителей и планирование маршруток")
    app.geometry("1200x600")
    app.configure(bg="white")
    mainFrame = Frame(app, bg="white")
    mainFrame.pack(fill="both", expand=True, padx=10, pady=10)
    centerFrame = Frame(mainFrame, bg="white")
    centerFrame.pack(side="top", expand=True)
    topFrame = Frame(centerFrame, bg="white")
    topFrame.pack(side="top")
    driverFrame = Frame(topFrame, bg="white")
    driverFrame.pack(side="left", padx=5)
    Label(driverFrame, text="Имя водителя:", bg="white", fg="black").pack(anchor=W)
    driverNameEntry = Entry(driverFrame, font=("Helvetica", 12), relief="solid", bd=2, bg="white", fg="black")
    driverNameEntry.pack()
    groupFrame = Frame(topFrame, bg="white")
    groupFrame.pack(side="left", padx=5)
    Label(groupFrame, text="Тип водителя:", bg="white", fg="black").pack(anchor=W)
    driverGroupVar = StringVar(app)
    driverGroupVar.set("A")
    groupSelector = OptionMenu(groupFrame, driverGroupVar, "A", "B")
    groupSelector.config(font=("Helvetica", 12), relief="solid", bd=2, bg="white", fg="black")
    groupSelector.pack()
    dayFrame = Frame(topFrame, bg="white")
    dayFrame.pack(side="left", padx=5)
    Label(dayFrame, text="День:", bg="white", fg="black").pack(anchor=W)
    selectedDay = StringVar(app)
    selectedDay.set("Понедельник")
    dayMenu = OptionMenu(dayFrame, selectedDay,"Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье")
    dayMenu.config(font=("Helvetica", 12), relief="solid", bd=2, bg="white", fg="black")
    dayMenu.pack()
    routesFrame = Frame(topFrame, bg="white")
    routesFrame.pack(side="left", padx=5)
    Label(routesFrame, text="Количество рейсов:", bg="white", fg="black").pack(anchor=W)
    routesEntry = Entry(routesFrame, font=("Helvetica", 12), relief="solid", bd=2, bg="white", fg="black")
    routesEntry.pack()
    timeFrame = Frame(topFrame, bg="white")
    timeFrame.pack(side="left", padx=5)
    Label(timeFrame, text="Время маршрута (мин):", bg="white", fg="black").pack(anchor=W)
    timeEntry = Entry(timeFrame, font=("Helvetica", 12), relief="solid", bd=2, bg="white", fg="black")
    timeEntry.pack()
    buttonFrame = Frame(topFrame, bg="white")
    buttonFrame.pack(side="left", padx=20)
    statusLabel = Label(topFrame, text="", bg="white", fg="black", font=("Helvetica", 12))
    statusLabel.pack(side="left", padx=10)
    btnAddDriver = Button(buttonFrame, text="Сохранить водителя", command=lambda: registerDriver(driverNameEntry, driverGroupVar, statusLabel), bg="blue", fg="white", font=("Helvetica", 12), relief="solid", bd=2)
    btnAddDriver.pack(pady=2, fill="x")
    btnApplyTime = Button(buttonFrame, text="Применить время маршрута", command=applyRouteDuration, bg="blue", fg="white", font=("Helvetica", 12), relief="solid", bd=2)
    btnApplyTime.pack(pady=2, fill="x")
    btnGenJoint = Button(buttonFrame, text="Создать общее расписание", command=genJointSchedule, bg="blue", fg="white", font=("Helvetica", 12), relief="solid", bd=2)
    btnGenJoint.pack(pady=2, fill="x")
    btnGenGenetic = Button(buttonFrame, text="Генетическое расписание (A и B)", command=genJointGeneticSchedule, bg="blue", fg="white", font=("Helvetica", 12), relief="solid", bd=2)
    btnGenGenetic.pack(pady=2, fill="x")
    btnReset = Button(buttonFrame, text="Очистить поля", command=clearInputs, bg="blue", fg="white", font=("Helvetica", 12), relief="solid", bd=2)
    btnReset.pack(pady=10, fill="x")
    global scheduleResultWidget
    scheduleResultWidget = Text(mainFrame, height=20, width=140, bg="white", fg="black", font=("Courier", 10), relief="solid", bd=2, wrap=WORD)
    scheduleResultWidget.pack(side="top", fill="both", expand=True, pady=10)
    app.mainloop()
if __name__ == "__main__":
    runApp()
