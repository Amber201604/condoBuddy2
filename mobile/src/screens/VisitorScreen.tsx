import React, { useEffect, useState } from "react";
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  TextInput, Modal, RefreshControl,
} from "react-native";
import { listVisitors, createVisitor } from "../api/client";

export default function VisitorScreen() {
  const [visitors, setVisitors] = useState<any[]>([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [form, setForm] = useState({ visitor_name: "", visitor_phone: "", visit_purpose: "", notes: "" });

  const load = async () => {
    setRefreshing(true);
    try {
      const res = await listVisitors();
      setVisitors(res.data);
    } finally { setRefreshing(false); }
  };

  useEffect(() => { load(); }, []);

  const submit = async () => {
    const now = new Date();
    const visitDate = new Date(now.getTime() + 3600000); // +1 hour default
    try {
      await createVisitor({ ...form, visit_date: visitDate.toISOString(), expected_duration_minutes: 60 });
      setModalVisible(false);
      load();
    } catch (e) {}
  };

  const statusIcon: Record<string, string> = {
    scheduled: "📅", checked_in: "✅", checked_out: "🚪", cancelled: "❌",
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>🚶 Visitors</Text>
        <TouchableOpacity style={styles.addBtn} onPress={() => setModalVisible(true)}>
          <Text style={styles.addBtnText}>+ Add</Text>
        </TouchableOpacity>
      </View>

      <ScrollView refreshControl={<RefreshControl refreshing={refreshing} onRefresh={load} />}>
        {visitors.map((v) => (
          <View key={v.id} style={styles.card}>
            <View style={styles.cardHeader}>
              <Text style={styles.cardName}>{v.visitor_name}</Text>
              <Text style={styles.statusIcon}>{statusIcon[v.status] || "•"}</Text>
            </View>
            <Text style={styles.cardDetail}>📞 {v.visitor_phone || "No phone"}</Text>
            <Text style={styles.cardDetail}>🎯 {v.visit_purpose || "No purpose"}</Text>
            <Text style={styles.cardDetail}>🔑 Access Code: {v.access_code || "—"}</Text>
          </View>
        ))}
      </ScrollView>

      <Modal visible={modalVisible} animationType="slide" transparent>
        <View style={styles.overlay}>
          <View style={styles.modal}>
            <Text style={styles.modalTitle}>Add Visitor</Text>
            <TextInput style={styles.input} placeholder="Visitor Name" placeholderTextColor="#888" value={form.visitor_name} onChangeText={(t) => setForm({ ...form, visitor_name: t })} />
            <TextInput style={styles.input} placeholder="Phone" placeholderTextColor="#888" value={form.visitor_phone} onChangeText={(t) => setForm({ ...form, visitor_phone: t })} keyboardType="phone-pad" />
            <TextInput style={styles.input} placeholder="Purpose" placeholderTextColor="#888" value={form.visit_purpose} onChangeText={(t) => setForm({ ...form, visit_purpose: t })} />
            <TextInput style={styles.input} placeholder="Notes" placeholderTextColor="#888" value={form.notes} onChangeText={(t) => setForm({ ...form, notes: t })} multiline />
            <TouchableOpacity style={styles.submitBtn} onPress={submit}>
              <Text style={styles.submitBtnText}>Add Visitor</Text>
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
  cardName: { fontSize: 15, fontWeight: "bold", color: "#fff" },
  statusIcon: { fontSize: 18 },
  cardDetail: { color: "#a0a0a0", fontSize: 13, marginBottom: 2 },
  overlay: { flex: 1, backgroundColor: "#000000cc", justifyContent: "center", padding: 20 },
  modal: { backgroundColor: "#16213e", borderRadius: 16, padding: 20 },
  modalTitle: { fontSize: 18, fontWeight: "bold", color: "#fff", marginBottom: 16 },
  input: { backgroundColor: "#0f3460", borderRadius: 8, padding: 12, color: "#fff", marginBottom: 10 },
  submitBtn: { backgroundColor: "#e94560", borderRadius: 8, padding: 14, alignItems: "center", marginTop: 10 },
  submitBtnText: { color: "#fff", fontWeight: "bold" },
  cancelText: { color: "#888", textAlign: "center", marginTop: 12 },
});
