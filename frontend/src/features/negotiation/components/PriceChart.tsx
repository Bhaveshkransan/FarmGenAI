import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function PriceChart({ data, isTransport = false }) {
  // Fallback data if none provided
  const chartData = data || [
    { name: 'Day 1', price: 18 },
    { name: 'Day 5', price: 19 },
    { name: 'Day 10', price: 18.5 },
    { name: 'Day 15', price: 21 },
    { name: 'Day 20', price: 22.5 },
    { name: 'Day 25', price: 22 },
    { name: 'Day 30', price: 24 },
  ];

  return (
    <div className="w-full h-64 mt-4">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <Line type="monotone" dataKey="price" stroke="#10b981" strokeWidth={3} dot={{ r: 4, fill: '#10b981' }} activeDot={{ r: 6 }} />
          <CartesianGrid stroke="#f1f5f9" strokeDasharray="5 5" vertical={false} />
          <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 12 }} dy={10} />
          <YAxis axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 12 }} dx={-10} tickFormatter={(val) => `₹${val}`} />
          <Tooltip 
            contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
            formatter={(value) => [isTransport ? `₹${value}` : `₹${value}/kg`, isTransport ? 'Freight Cost' : 'Modal Price']}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
