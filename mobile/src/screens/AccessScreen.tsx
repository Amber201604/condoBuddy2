import React, { useEffect, useState } from "react";
import { View, Text, ScrollView, StyleSheet, TouchableOpacity, RefreshControl } from "react-native";
import { listAccessLogs } from "../api/client";

export default function AccessScreen() {
  const [logs, setLogs] = useState<any[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    setRefreshing(true);
    try {
      const res = await listAccessLogs({ limit: 50 });
      setLogs(res.data);
    } finally { setRefreshing(false); }
  };

  useEffect(() => { load(); }, []);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>🔑 Access Control</Text>
      </View>

      <View style={styles.quickRow}>
        <TouchableOpacity style={styles.bigBtn}>
          <Text style={styles.bigBtnIcon}>🚪</Text>
          <Text style={styles.bigBtnText}>Open Main Door</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.bigBtn}>
          <Text style={styles.bigBtnIcon}>🛗</Text>
          <Text style={styles.bigBtnText}>Call Elevator</Text>
        </TouchableOpacity>
      </View>

      <Text style={styles.sectionTitle}>Recent Access Logs</Text>
      <ScrollView refreshControl={<RefreshControl refreshing={refreshing} onRefresh={load} />}>
        {logs.map((log) => (
          <View key={log.id} style={styles.logCard}>
            <Text style={styles.logMethod}>{log.access_method.toUpperCase()}</Text>
            <Text style={styles.logPoint}>{log.entry_point}</Text>
            <Text style={styles.logTime}>{new Date(log.timestamp).toLocaleString()}</Text>
            <View style={[styles.dirBadge, { backgroundColor: log.direction === "entry" ? "#2ecc71" : "#e94560" }]}>
              <Text style={styles.dirText}>{log.direction}</Text>
            </View>
          </View>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#1a1a2e" },
  header: { padding: 16, paddingTop: 50 },
  title: { fontSize: 22, fontWeight: "bold", color: "#fff" },
  quickRow: { flexDirection: "row", padding: 16, gap: 12 },
  bigBtn: {
    flex: 1,
    backgroundColor: "#16213e",
    borderRadius: 14,
    padding: 20,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#0f3460",
  },
  bigBtnIcon: { fontSize: 32, marginBottom: 8 },
  bigBtnText: { color: "#fff", fontWeight: "bold", fontSize: 13 },
  sectionTitle: { fontSize: 16, fontWeight: "bold", color: "#fff", paddingHorizontal: 16, marginBottom: 8 },
  logCard: {
    backgroundColor: "#16213e",
    marginHorizontal: 16,
    marginBottom: 8,
    borderRadius: 10,
    padding: 12,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    borderWidth: 1,
    borderColor: "#0f3460",
  },
  logMethod: { color: "#e94560", fontWeight: "bold", fontSize: 12, width: 60 },
  logPoint: { color: "#fff", fontSize: 13, flex: 1 },
  logTime: { color: "#888", fontSize: 11 },
  dirBadge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4 },
  dirText: { color: "#fff", fontSize: 10, fontWeight: "bold" },
});
