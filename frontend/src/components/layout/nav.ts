import {
  BarChart3,
  Boxes,
  ClipboardList,
  LayoutDashboard,
  Receipt,
  Undo2,
  ShoppingCart,
  Tags,
  Truck,
  UserCog,
  Users,
  Package,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { Role } from '@/types';

export interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
  end?: boolean;
  roles?: Role[]; // না দিলে সবার জন্য
}

export interface NavGroup {
  title: string;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    title: 'Main',
    items: [
      { label: 'Dashboard', to: '/', icon: LayoutDashboard, end: true },
      { label: 'POS / New Sale', to: '/pos', icon: ShoppingCart },
      { label: 'Sales', to: '/sales', icon: Receipt },
      { label: 'Returns', to: '/returns', icon: Undo2 },
    ],
  },
  {
    title: 'Catalog',
    items: [
      { label: 'Products', to: '/products', icon: Package },
      { label: 'Categories', to: '/categories', icon: Tags },
      { label: 'Inventory', to: '/inventory', icon: Boxes },
    ],
  },
  {
    title: 'Contacts',
    items: [
      { label: 'Customers', to: '/customers', icon: Users },
      { label: 'Suppliers', to: '/suppliers', icon: Truck },
    ],
  },
  {
    title: 'Management',
    items: [
      { label: 'Purchases', to: '/purchases', icon: ClipboardList, roles: ['admin'] },
      { label: 'Reports', to: '/reports', icon: BarChart3, roles: ['admin'] },
      { label: 'Users', to: '/users', icon: UserCog, roles: ['admin'] },
    ],
  },
];
