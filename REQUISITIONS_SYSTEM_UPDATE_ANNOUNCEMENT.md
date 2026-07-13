# 🎉 Major Requisitions System Update - Team Announcement

## Overview
We're excited to announce a **major update** to our Requisitions Management System! The system has been significantly enhanced with new features including **Department/Unit Management**, **Store Management**, **role-based access control**, and **multi-store support**. This update provides better organization, security, and flexibility for managing inventory requests across the hospital.

---

## 🆕 What's New

### 1. **Department/Unit Management System**
- **Renamed from "Ward Management"** to **"Department/Unit Management"**
- All departments/units are now managed dynamically (no more hardcoded lists!)
- Departments can be categorized by type:
  - **Ward** - Appears in IPD activities (admissions, transfers, etc.)
  - **OPD** - Outpatient Department
  - **IT Unit** - IT Department
  - **Administration** - Admin Department
  - **Pharmacy** - Pharmacy Department
  - **Other** - Other departments
- Only departments with type "Ward" appear in IPD activities
- All departments can request items from stores via Requisitions

### 2. **Store Management System**
- New **Store Management** module for managing hospital stores
- Pre-configured stores: **Main Store** and **Pharmacy Store**
- Additional stores can be created as needed
- Each store can have assigned staff (Store Managers and Department Heads)

### 3. **Staff Assignment System**

#### **Department Staff Assignments (IC/Deputy)**
- Departments can now have assigned **In-Charge (IC)** and **Deputy** staff
- **Only IC and Deputies can create requisitions** for their assigned departments
- Prevents unauthorized requisition creation
- Searchable staff selection (by name and username) for easy assignment

#### **Store Staff Assignments (Store Manager/Department Head)**
- Stores can have assigned **Store Managers** and **Department Heads**
- Assigned staff automatically see only requisitions from their assigned stores
- Store filter is automatically locked for assigned staff
- Admins can freely switch between stores

### 4. **Multi-Store Support**
- Requisitions are now **store-based** (not just pharmacy store)
- Departments can request items from any store (Main Store, Pharmacy Store, etc.)
- Each requisition specifies which store it's requesting from
- Store Managers/Department Heads only see requisitions for their assigned stores

### 5. **Enhanced Store Filtering**
- **Requisitions Page**: Added store filter dropdown
  - Store Managers/Department Heads: Automatically filtered and locked to their assigned stores
  - Admins: Can freely switch between stores
- **Department/Unit Stock Page**: Added store filter
  - Shows items from specific stores
  - Store Managers/Department Heads: Automatically filtered to their assigned stores
  - Displays store name for each stock item

### 6. **Pharmacy Head Can Now Fulfill**
- **Pharmacy Head** can now fulfill requisitions (in addition to Store Manager)
- Provides flexibility when Store Managers are unavailable
- Same fulfillment capabilities as Store Managers

### 7. **Improved Access Control**
- **Department IC/Deputy**: Can only create requisitions for their assigned departments
- **Store Managers/Department Heads**: Automatically see only requisitions from assigned stores
- **Pharmacy Head**: Can approve/reject and fulfill requisitions (sees all stores)
- **Admin**: Full access to all features

---

## 🔄 Updated Workflow

### The Complete Workflow:
1. **Department IC/Deputy** creates requisition for their department from a specific store
2. **Pharmacy Head** reviews and approves/rejects requests
3. **Store Manager** or **Pharmacy Head** fulfills approved requests (supports partial fulfillment)
4. Items are added to department/unit stock **with store tracking**
5. Department staff can then debit items to clients for billing

---

## ✨ Key Features

### 1. **Department/Unit Management**
- Create, edit, and manage departments/units dynamically
- Assign department types (Ward, OPD, IT, Admin, Pharmacy, Other)
- Assign IC and Deputies to departments
- Only wards appear in IPD activities

### 2. **Store Management**
- Create and manage stores (Main Store, Pharmacy Store, etc.)
- Assign Store Managers and Department Heads to stores
- Track which store provided items to each department

### 3. **Smart Access Control**
- IC/Deputy restriction: Only assigned staff can create requisitions
- Store-based filtering: Staff only see requisitions from their assigned stores
- Automatic filtering: No manual selection needed for assigned staff

### 4. **Store-Based Stock Tracking**
- Department/Unit Stock now tracks which store provided each item
- Filter stock by store to see items from specific stores
- Store Managers/Department Heads automatically see stock from their stores only

### 5. **Enhanced Requisitions Page**
- **Store Filter**: Filter requisitions by store
  - Auto-locked for Store Managers/Department Heads
  - Free selection for Admins
- **Date Range Filtering**: Filter by start and end dates (persists across actions)
- **Department/Unit Filter**: Filter by department/unit
- **Status Filter**: Filter by requisition status

### 6. **Duplicate Request Prevention**
- System prevents creating duplicate requests for items with pending requisitions
- Staff are notified with details of existing pending requests
- Option to cancel pending requests if needed

### 7. **Partial Fulfillment**
- Store Managers and Pharmacy Head can partially fulfill requests
- System tracks fulfilled vs. requested quantities
- Remaining quantities can be fulfilled later

### 8. **Comprehensive Audit Trail**
- Complete history of all requisition actions
- Tracks who performed each action and when
- Includes notes and reasons for transparency

### 9. **Smart Notifications**
- Real-time notifications for all requisition events
- Notifications sent to relevant staff based on roles

---

## 👥 Roles & Responsibilities

### **Department IC/Deputy** (In-Charge/Deputy)
- **Can create requisitions** for their assigned department only
- View requisition status and history for their department
- Cancel pending requisitions
- View department/unit stock levels
- Debit items to clients (only after items are in stock)

### **Pharmacy Head**
- Review and approve/reject requisition requests from all departments
- **Can fulfill approved requisitions** (new!)
- View all requisitions across all stores
- Check department/unit stock levels
- Full access to pharmacy management features

### **Store Manager**
- Fulfill approved requisitions for **assigned stores only**
- Automatically filtered to see only requisitions from assigned stores
- Support partial fulfillment when needed
- View department/unit stock for assigned stores
- Access to pharmacy management features

### **Department Head** (Store Assignment)
- Same as Store Manager
- Automatically filtered to assigned stores
- Can fulfill requisitions for assigned stores

### **Admin**
- Full access to all features
- Can manage departments/units and stores
- Can assign staff to departments and stores
- Can view all requisitions from all stores
- Can switch between stores freely

---

## 📋 How to Use

### Managing Departments/Units:
1. Navigate to **IPD → Department Management**
2. Create new departments/units with appropriate types
3. Assign IC and Deputies to departments
4. Only departments with type "Ward" will appear in IPD activities

### Managing Stores:
1. Navigate to **Admin → Store Management**
2. View existing stores (Main Store, Pharmacy Store)
3. Create additional stores if needed
4. Assign Store Managers and Department Heads to stores

### Creating a Requisition (IC/Deputy Only):
1. Navigate to **Requisitions** page
2. Click **"Create Requisition"** button
3. Select your **department/unit** (only your assigned departments appear)
4. Select the **store** to request from
5. Add items by searching and selecting products
6. Enter quantities and optional notes
7. Submit the requisition

### Approving/Rejecting (Pharmacy Head):
1. View pending requisitions in the table
2. Use **store filter** if needed (Admins only)
3. Click **"View"** to see full details
4. Click **"Approve"** or **"Reject"**
5. If rejecting, add an optional reason/comment

### Fulfilling (Store Manager/Pharmacy Head):
1. View approved requisitions
   - Store Managers/Department Heads: Automatically see only their assigned stores
   - Pharmacy Head: See all stores
2. Click **"Fulfill"** on an approved requisition
3. Enter fulfilled quantities for each item (can be partial)
4. Add fulfillment notes if needed
5. Submit - items will be added to department/unit stock with store tracking

### Viewing Department/Unit Stock:
1. Click **"View Department/Unit Stock"** button
2. Select a department/unit to see all available stock
3. Use **store filter** to see items from specific stores
   - Store Managers/Department Heads: Automatically filtered to assigned stores
4. Check quantities before creating new requisitions

---

## 🔒 Important Rules

1. **Only IC/Deputy can create requisitions**
   - Staff must be assigned as IC or Deputy to a department to create requisitions
   - Contact Admin to get assigned to your department

2. **Store-based access control**
   - Store Managers and Department Heads only see requisitions from their assigned stores
   - This prevents accidentally approving/fulfilling requests from wrong stores

3. **Items can only be debited AFTER they are in department/unit stock**
   - If stock is insufficient, you'll be prompted to request from stores first

4. **No duplicate pending requests**
   - If an item has a pending requisition, you must wait for approval/rejection or cancel it

5. **Requisitions can only be cancelled if pending**
   - Once approved or rejected, they cannot be cancelled

6. **Partial fulfillment is allowed**
   - Store Managers and Pharmacy Head can fulfill part of a request and complete the rest later

7. **IPD activities show only Wards**
   - Only departments with type "Ward" appear in IPD activities (admissions, transfers, etc.)
   - Other department types can still request items but don't appear in IPD

---

## 📊 Benefits

- ✅ **Better Organization**: Dynamic department/unit and store management
- ✅ **Enhanced Security**: Role-based access control prevents unauthorized actions
- ✅ **Multi-Store Support**: Request items from different stores (Main Store, Pharmacy Store, etc.)
- ✅ **Prevents Mistakes**: Store Managers only see requisitions from their assigned stores
- ✅ **Better Tracking**: Know which store provided items to each department
- ✅ **Flexibility**: Pharmacy Head can fulfill when Store Managers are unavailable
- ✅ **Transparency**: Complete audit trail of all actions
- ✅ **Efficiency**: Streamlined workflow with automatic filtering
- ✅ **Accountability**: Know who requested, approved, and fulfilled each item

---

## 🆘 Need Help?

If you have any questions or encounter issues:
- Check the in-app help messages on each page
- Contact the Admin team for:
  - Department/Unit assignments (IC/Deputy)
  - Store assignments (Store Manager/Department Head)
  - Access issues
- Review the requisition history for any requisition to see what happened

---

## 🎯 Next Steps

1. **Familiarize yourself** with the new Department/Unit and Store Management features
2. **Check your assignments**: Ensure you're assigned as IC/Deputy to your department if you need to create requisitions
3. **Start using the new system** for all inventory requests
4. **Provide feedback** if you notice any issues or have suggestions

---

## 📝 Summary of Changes

- ✅ Renamed "Pharmacy Requisitions" to "Requisitions" (multi-store support)
- ✅ Added Department/Unit Management with types
- ✅ Added Store Management
- ✅ Added staff assignments (IC/Deputy for departments, Store Manager/Department Head for stores)
- ✅ Only IC/Deputy can create requisitions
- ✅ Store Managers/Department Heads automatically filtered to assigned stores
- ✅ Added store filtering to Requisitions and Department/Unit Stock pages
- ✅ Pharmacy Head can now fulfill requisitions
- ✅ Store-based stock tracking
- ✅ IPD pages show only Wards

Thank you for your cooperation as we implement these improvements!

---

*Last Updated: [Current Date]*

