import React, { useEffect, useState } from "react";
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  TextInput, Modal, RefreshControl,
} from "react-native";
import { listWorkOrders, createWorkOrder } from "../api/client";

const CATEGORIES = ["maintenance", "cleaning", "security", "hvac", "plumbing", "electrical", "other"];
const PRIORITIES = ["low", "medium", "high", "urgent"];

export default function WorkOrderScreen() {
  const [orders, setOrders] = useState<any[]>([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", category: "maintenance", priority: "medium", unit_number: "" });

  const load = async () => {
    setRefreshing(true);
    try {
      const res = await listWorkOrders();
      setOrders(res.data);
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => { load(); }, []);

  const submit = async () => {
    try {
      await createWorkOrder(form);
      setModalVisible(false);
      load();
    } catch (e) {
      // show error
    }
  };

  const statusColor: Record<string, string> = {
    open: "#e94560", assigned: "#f0a500", in_progress: "#3498db",
    pending_parts: "#9b59b6", completed: "#2ecc71", cancelled: "#95a5a6",
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>🔧 Work Orders</Text>
        <TouchableOpacity style={styles.addBtn} onPress={() => setModalVisible(true)}>
          <Text style={styles.addBtnText}>+ New</Text>
        </TouchableOpacity>
      </View>

      <ScrollView
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={load} />}
      >
        {orders.map((o) => (
          <View key={o.id} style={styles.card}>
            <View style={styles.cardHeader}>
              <Text style={styles.cardTitle}>{o.title}</Text>
              <View style={[styles.badge, { backgroundColor: statusColor[o.status] || "#888" }]}>
                <Text style={styles.badgeText}>{o.status}</Text>
              </View>
            </View>
            <Text style={styles.cardDesc}>{o.description || "No description"}</Text>
            <Text style={styles.cardMeta}>📍 {o.unit_number}  •  🏷️ {o.category}  •  ⚡ {o.priority}</Text>
          </View>
        ))}
      </ScrollView>

      <Modal visible={modalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modal}>
            <Text style={styles.modalTitle}>New Work Order</Text>
            <TextInput style={styles.input} placeholder="Title" placeholderTextColor="#888" value={form.title} onChangeText={(t) => setForm({ ...form, title: t })} />
            <TextInput style={styles.input} placeholder="Description" placeholderTextColor="#888" value={form.description} onChangeText={(t) => setForm({ ...form, description: t })} multiline />
            <TextInput style={styles.input} placeholder="Unit Number" placeholderTextColor="#888" value={form.unit_number} onChangeText={(t) => setForm({ ...form, unit_number: t })} />
            <View style={styles.row}>
              {CATEGORIES.map((c) => (
                <TouchableOpacity key={c} style={[styles.chip, form.category === c && styles.chipActive]} onPress={() => setForm({ ...form, category: c })}>
                  <Text style={form.category === c ? styles.chipTextActive : styles.chipText}>{c}</Text>
                </TouchableOpacity>
              ))}
            </View>
            <View style={styles.row}>
              {PRIORITIES.map((p) => (
                <TouchableOpacity key={p} style={[styles.chip, form.priority === p && styles.chipActive]} onPress={() => setForm({ ...form, priority: p })}>
                  <Text style={form.priority === p ? styles.chipTextActive : styles.chipText}>{p}</Text>
                </TouchableOpacity>
              ))}
            </View>
            <TouchableOpacity style={styles.submitBtn} onPress={submit}>
              <Text style={styles.submitBtnText}>Submit</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={() => setModalVisible(false)}>
              <Text style={styles.cancelText}>Cancel</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#1a1a2e" },
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", padding: 16, paddingTop: 50 },
  title: { fontSize: 22, fontWeight: "bold", color: "#fff" },
  addBtn: { backgroundColor: "#e94560", paddingHorizontal: 16, paddingVertical: 8, borderRadius: 8 },
  addBtnText: { color: "#fff", fontWeight: "bold" },
  card: { backgroundColor: "#16213e", marginHorizontal: 16, marginBottom: 10, borderRadius: 12, padding: 14, borderWidth: 1, borderColor: "#0f3460" },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 6 },
  cardTitle: { fontSize: 15, fontWeight: "bold", color: "#fff", flex: 1 },
  badge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4 },
  badgeText: { color: "#fff", fontSize: 10, fontWeight: "bold" },
  cardDesc: { color: "#a0a0a0", fontSize: 13, marginBottom: 6 },
  cardMeta: { color: "#888", fontSize: 11 },
  modalOverlay: { flex: 1, backgroundColor: "#000000cc", justifyContent: "center", padding: 20 },
  modal: { backgroundColor: "#16213e", borderRadius: 16, padding: 20 },
  modalTitle: { fontSize: 18, fontWeight: "bold", color: "#fff", marginBottom: 16 },
  input: { backgroundColor: "#0f3460", borderRadius: 8, padding: 12, color: "#fff", marginBottom: 10 },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginBottom: 10 },
  chip: { backgroundColor: "#0f3460", paddingHorizontal: 10, paddingVertical: 6, borderRadius: 6 },
  chipActive: { backgroundColor: "#e94560" },
  chipText: { color: "#a0a0a0", fontSize: 12 },
  chipTextActive: { color: "#fff", fontWeight: "bold", fontSize: 12 },
  submitBtn: { backgroundColor: "#e94560", borderRadius: 8, padding: 14, alignItems: "center", marginTop: 10 },
  submitBtnText: { color: "#fff", fontWeight: "bold" },
  cancelText: { color: "#888", textAlign: "center", marginTop: 12 },
});
