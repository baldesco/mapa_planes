-- Migration to enable and optimize Row Level Security (RLS) on visit_photos table
-- Created on 2026-05-24

-- 1. Enable Row Level Security
ALTER TABLE public.visit_photos ENABLE ROW LEVEL SECURITY;

-- 2. Performance Index for user_id lookup in RLS policies
CREATE INDEX IF NOT EXISTS idx_visit_photos_user_id ON public.visit_photos(user_id);

-- 3. Drop existing policies if they already exist
DROP POLICY IF EXISTS "Users can view their own visit photos" ON public.visit_photos;
DROP POLICY IF EXISTS "Users can insert their own visit photos" ON public.visit_photos;
DROP POLICY IF EXISTS "Users can update their own visit photos" ON public.visit_photos;
DROP POLICY IF EXISTS "Users can delete their own visit photos" ON public.visit_photos;

-- 4. Create policies with (select auth.uid()) subquery optimization
-- (Evaluates auth.uid() once per query rather than once per row)

-- SELECT policy: Users can only view photos associated with their user_id
CREATE POLICY "Users can view their own visit photos"
    ON public.visit_photos
    FOR SELECT
    TO authenticated
    USING ((select auth.uid()) = user_id);

-- INSERT policy: Users can only upload/insert photos for their user_id
CREATE POLICY "Users can insert their own visit photos"
    ON public.visit_photos
    FOR INSERT
    TO authenticated
    WITH CHECK ((select auth.uid()) = user_id);

-- UPDATE policy: Users can only update their own photos
CREATE POLICY "Users can update their own visit photos"
    ON public.visit_photos
    FOR UPDATE
    TO authenticated
    USING ((select auth.uid()) = user_id)
    WITH CHECK ((select auth.uid()) = user_id);

-- DELETE policy: Users can only delete their own photos
CREATE POLICY "Users can delete their own visit photos"
    ON public.visit_photos
    FOR DELETE
    TO authenticated
    USING ((select auth.uid()) = user_id);
