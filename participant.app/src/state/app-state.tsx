import React, { createContext, useContext, useMemo, useState } from "react";

type QrArrivalRecord = {
  operationId: number;
  passengerTc: string;
  role: "driver" | "greeter";
  recordedAt: number;
};

type PassengerMarksByOperation = Record<number, string[]>;
type StageIndexByOperation = Record<number, number>;
type SelectedOperationContext = {
  operationLabel?: string | null;
  projectName?: string | null;
  jobTime?: string | null;
};

type AppStateContextValue = {
  readNotificationIds: number[];
  setReadNotificationIds: React.Dispatch<React.SetStateAction<number[]>>;
  readAlertIds: number[];
  setReadAlertIds: React.Dispatch<React.SetStateAction<number[]>>;
  qrArrivalRecords: QrArrivalRecord[];
  markQrArrival: (record: QrArrivalRecord) => void;
  passengerMarksByOperation: PassengerMarksByOperation;
  togglePassengerMark: (operationId: number, passengerTc: string) => void;
  stageIndexByOperation: StageIndexByOperation;
  setOperationStageIndex: (operationId: number, stageIndex: number) => void;
  selectedOperationContext: SelectedOperationContext | null;
  setSelectedOperationContext: React.Dispatch<React.SetStateAction<SelectedOperationContext | null>>;
};

const AppStateContext = createContext<AppStateContextValue | null>(null);

export function AppStateProvider({ children }: { children: React.ReactNode }) {
  const [readNotificationIds, setReadNotificationIds] = useState<number[]>([]);
  const [readAlertIds, setReadAlertIds] = useState<number[]>([]);
  const [qrArrivalRecords, setQrArrivalRecords] = useState<QrArrivalRecord[]>([]);
  const [passengerMarksByOperation, setPassengerMarksByOperation] = useState<PassengerMarksByOperation>({});
  const [stageIndexByOperation, setStageIndexByOperation] = useState<StageIndexByOperation>({});
  const [selectedOperationContext, setSelectedOperationContext] = useState<SelectedOperationContext | null>(null);

  const value = useMemo<AppStateContextValue>(
    () => ({
      readNotificationIds,
      setReadNotificationIds,
      readAlertIds,
      setReadAlertIds,
      qrArrivalRecords,
      markQrArrival: (record) => {
        setQrArrivalRecords((prev) => {
          const existingIndex = prev.findIndex(
            (item) =>
              item.operationId === record.operationId &&
              item.passengerTc === record.passengerTc &&
              item.role === record.role,
          );

          if (existingIndex >= 0) {
            const next = [...prev];
            next[existingIndex] = record;
            return next;
          }

          return [...prev, record];
        });
      },
      passengerMarksByOperation,
      togglePassengerMark: (operationId, passengerTc) => {
        setPassengerMarksByOperation((prev) => {
          const current = prev[operationId] ?? [];
          const exists = current.includes(passengerTc);
          return {
            ...prev,
            [operationId]: exists
              ? current.filter((item) => item !== passengerTc)
              : [...current, passengerTc],
          };
        });
      },
      stageIndexByOperation,
      setOperationStageIndex: (operationId, stageIndex) => {
        setStageIndexByOperation((prev) => ({
          ...prev,
          [operationId]: stageIndex,
        }));
      },
      selectedOperationContext,
      setSelectedOperationContext,
    }),
    [
      passengerMarksByOperation,
      qrArrivalRecords,
      readAlertIds,
      readNotificationIds,
      selectedOperationContext,
      stageIndexByOperation,
    ],
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState() {
  const context = useContext(AppStateContext);
  if (!context) {
    throw new Error("useAppState must be used inside AppStateProvider");
  }
  return context;
}
